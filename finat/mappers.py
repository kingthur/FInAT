from collections import deque
from pymbolic.mapper import IdentityMapper as IM
from pymbolic.mapper.stringifier import StringifyMapper, PREC_NONE
from pymbolic.mapper import WalkMapper as WM
from pymbolic.mapper.graphviz import GraphvizMapper as GVM
from .indices import IndexBase
from .ast import Recipe, ForAll, IndexSum, Let, Variable
try:
    from termcolor import colored
except ImportError:
    def colored(string, color, attrs=[]):
        return string


class IdentityMapper(IM):
    def __init__(self):
        super(IdentityMapper, self).__init__()

    def map_recipe(self, expr, *args, **kwargs):
        return expr.__class__(self.rec(expr.indices, *args, **kwargs),
                              self.rec(expr.body, *args, **kwargs),
                              expr._transpose)

    def map_index(self, expr, *args, **kwargs):
        return expr

    def map_delta(self, expr, *args, **kwargs):
        return expr.__class__(*(self.rec(c, *args, **kwargs)
                                for c in expr.children))

    def map_inverse(self, expr, *args, **kwargs):
        return expr.__class__(self.rec(expr.expression, *args, **kwargs))

    map_let = map_delta
    map_for_all = map_delta
    map_wave = map_delta
    map_index_sum = map_delta
    map_levi_civita = map_delta
    map_compound_vector = map_delta
    map_det = map_inverse
    map_abs = map_inverse


class _IndexMapper(IdentityMapper):
    def __init__(self, replacements):
        super(_IndexMapper, self).__init__()

        self.replacements = replacements

    def map_index(self, expr, *args, **kwargs):
        '''Replace indices if they are in the replacements list'''

        try:
            return(self.replacements[expr])
        except KeyError:
            return expr

    def map_recipe(self, expr, *args, **kwargs):
        indices = self.rec(expr.indices, *args, **kwargs)
        indices = tuple(tuple(i for i in ii if isinstance(i, IndexBase))
                        for ii in indices)

        return expr.__class__(indices,
                              self.rec(expr.body, *args, **kwargs),
                              expr._transpose)


class _StringifyMapper(StringifyMapper):

    def map_recipe(self, expr, enclosing_prec, indent=None, *args, **kwargs):
        if indent is None:
            fmt = expr.name + "(%s, %s)"
        else:
            oldidt = " " * indent
            indent += 4
            idt = " " * indent
            fmt = expr.name + "(%s,\n" + idt + "%s\n" + oldidt + ")"

        return self.format(fmt,
                           self.rec(expr.indices, PREC_NONE, indent=indent, *args, **kwargs),
                           self.rec(expr.body, PREC_NONE, indent=indent, *args, **kwargs))

    map_for_all = map_recipe

    def map_let(self, expr, enclosing_prec, indent=None, *args, **kwargs):
        if indent is None:
            fmt = expr.name + "(%s, %s)"
            inner_indent = None
        else:
            oldidt = " " * indent
            indent += 4
            inner_indent = indent + 4
            inner_idt = " " * inner_indent
            idt = " " * indent
            fmt = expr.name + "(\n" + inner_idt + "%s,\n" + idt + "%s\n" + oldidt + ")"

        return self.format(fmt,
                           self.rec(expr.bindings, PREC_NONE, indent=inner_indent, *args, **kwargs),
                           self.rec(expr.body, PREC_NONE, indent=indent, *args, **kwargs))

    def map_delta(self, expr, *args, **kwargs):
        return self.format(expr.name + "(%s, %s)",
                           *[self.rec(c, *args, **kwargs) for c in expr.children])

    def map_index(self, expr, *args, **kwargs):
        if hasattr(expr, "_error"):
            return colored(str(expr), "red", attrs=["bold"])
        else:
            return colored(str(expr), expr._color)

    def map_wave(self, expr, enclosing_prec, indent=None, *args, **kwargs):
        if indent is None or enclosing_prec is not PREC_NONE:
            fmt = expr.name + "(%s %s) "
        else:
            oldidt = " " * indent
            indent += 4
            idt = " " * indent
            fmt = expr.name + "(%s\n" + idt + "%s\n" + oldidt + ")"

        return self.format(fmt,
                           " ".join(self.rec(c, PREC_NONE, *args, **kwargs) + "," for c in expr.children[:-1]),
                           self.rec(expr.children[-1], PREC_NONE, indent=indent, *args, **kwargs))

    def map_index_sum(self, expr, enclosing_prec, indent=None, *args, **kwargs):
        if indent is None or enclosing_prec is not PREC_NONE:
            fmt = expr.name + "((%s), %s) "
        else:
            oldidt = " " * indent
            indent += 4
            idt = " " * indent
            fmt = expr.name + "((%s),\n" + idt + "%s\n" + oldidt + ")"

        return self.format(fmt,
                           " ".join(self.rec(c, PREC_NONE, *args, **kwargs) + "," for c in expr.children[0]),
                           self.rec(expr.children[1], PREC_NONE, indent=indent, *args, **kwargs))

    def map_levi_civita(self, expr, *args, **kwargs):
        return self.format(expr.name + "(%s)",
                           self.join_rec(", ", expr.children, *args, **kwargs))

    def map_inverse(self, expr, *args, **kwargs):
        return self.format(expr.name + "(%s)",
                           self.rec(expr.expression, *args, **kwargs))

    def map_det(self, expr, *args, **kwargs):
        return self.format(expr.name + "(%s)",
                           self.rec(expr.expression, *args, **kwargs))

    map_abs = map_det

    def map_compound_vector(self, expr, *args, **kwargs):
        return self.format(expr.name + "(%s)",
                           self.join_rec(", ", expr.children, *args, **kwargs))

    def map_variable(self, expr, enclosing_prec, *args, **kwargs):
        if hasattr(expr, "_error"):
            return colored(str(expr.name), "red", attrs=["bold"])
        else:
            try:
                return colored(expr.name, expr._color)
            except AttributeError:
                return colored(expr.name, "cyan")


class WalkMapper(WM):
    def __init__(self):
        super(WalkMapper, self).__init__()

    def map_recipe(self, expr, *args, **kwargs):
        if not self.visit(expr, *args, **kwargs):
            return
        for indices in expr.indices:
            for index in indices:
                self.rec(index, *args, **kwargs)
        self.rec(expr.body, *args, **kwargs)
        self.post_visit(expr, *args, **kwargs)

    def map_index(self, expr, *args, **kwargs):
        if not self.visit(expr, *args, **kwargs):
            return

        # I don't want to recur on the extent.  That's ugly.

        self.post_visit(expr, *args, **kwargs)

    def map_index_sum(self, expr, *args, **kwargs):
        if not self.visit(expr, *args, **kwargs):
            return
        for index in expr.indices:
            self.rec(index, *args, **kwargs)
        self.rec(expr.body, *args, **kwargs)
        self.post_visit(expr, *args, **kwargs)

    map_delta = map_index_sum
    map_for_all = map_index_sum
    map_wave = map_index_sum
    map_levi_civita = map_index_sum
    map_inverse = map_index_sum
    map_det = map_index_sum
    map_compound_vector = map_index_sum


class GraphvizMapper(WalkMapper, GVM):
    pass


class BindingMapper(IdentityMapper):
    """A mapper that binds free indices in recipes using ForAlls."""

    def __init__(self, kernel_data):
        """
        :arg context: a mapping from variable names to values
        """
        super(BindingMapper, self).__init__()

    def map_recipe(self, expr, bound_above=None, bound_below=None):
        if bound_above is None:
            bound_above = set()
        if bound_below is None:
            bound_below = deque()

        body = self.rec(expr.body, bound_above, bound_below)

        d, b, p = expr.indices
        recipe_indices = tuple([i for i in d + b + p
                                if i not in bound_above])
        free_indices = tuple([i for i in recipe_indices
                              if i not in bound_below])

        bound_below.extendleft(reversed(free_indices))
        # Calculate the permutation from the order of loops actually
        # employed to the ordering of indices in the Recipe.
        try:
            def expand_tensors(indices):
                result = []
                if indices:
                    for i in indices:
                        try:
                            result += i.factors
                        except AttributeError:
                            result.append(i)
                return result

            tmp = expand_tensors(recipe_indices)
            transpose = [tmp.index(i) for i in expand_tensors(bound_below)]
        except ValueError:
            print "recipe_indices", recipe_indices
            print "missing index", i
            i.set_error()
            raise

        if len(free_indices) > 0:
            expr = Recipe(expr.indices, ForAll(free_indices, body),
                          _transpose=transpose)
        else:
            expr = Recipe(expr.indices, body, _transpose=transpose)

        return expr

    def map_let(self, expr, bound_above, bound_below):

        # Indices bound in the Let bindings should not count as
        # bound_below for nodes higher in the tree.
        return Let(tuple((symbol, self.rec(letexpr, bound_above,
                                           bound_below=None))
                         for symbol, letexpr in expr.bindings),
                   self.rec(expr.body, bound_above, bound_below))

    def map_index_sum(self, expr, bound_above, bound_below):
        indices = expr.indices
        for idx in indices:
            bound_above.add(idx)
        body = self.rec(expr.body, bound_above, bound_below)
        for idx in indices:
            bound_above.remove(idx)
        return IndexSum(indices, body)

    def map_for_all(self, expr, bound_above, bound_below):
        indices = expr.indices
        for idx in indices:
            bound_above.add(idx)
        body = self.rec(expr.body, bound_above, bound_below)
        for idx in indices:
            bound_above.remove(idx)
            bound_below.appendleft(idx)
        return ForAll(indices, body)


class IndexSumMapper(IdentityMapper):
    """A mapper that binds unbound IndexSums to temporary variables
    using Lets."""

    def __init__(self, kernel_data):
        """
        :arg context: a mapping from variable names to values
        """
        super(IndexSumMapper, self).__init__()
        self.kernel_data = kernel_data
        self._isum_stack = {}
        self._bound_isums = set()

    def _bind_isums(self, expr):
        bindings = []
        if isinstance(expr, Variable):
            children = (expr,)
        elif hasattr(expr, "children"):
            children = expr.children
        else:
            return expr

        for temp in children:
            if temp in self._isum_stack:
                isum = self._isum_stack[temp]
                bindings.append((temp, isum))
        for temp, isum in bindings:
            del self._isum_stack[temp]
        if len(bindings) > 0:
            expr = Let(tuple(bindings), expr)
        return expr

    def map_recipe(self, expr):
        body = self._bind_isums(self.rec(expr.body))
        return Recipe(expr.indices, body)

    def map_let(self, expr):
        # Record IndexSums already bound to a temporary
        new_bindings = []
        for v, e in expr.bindings:
            if isinstance(e, IndexSum):
                self._bound_isums.add(e)
            new_bindings.append((v, self.rec(e)))

        body = self._bind_isums(self.rec(expr.body))
        return Let(tuple(new_bindings), body)

    def map_index_sum(self, expr):
        if expr in self._bound_isums:
            return super(IndexSumMapper, self).map_index_sum(expr)

        # Replace IndexSum with temporary and add to stack
        temp = self.kernel_data.new_variable("isum")
        body = self._bind_isums(self.rec(expr.body))
        expr = IndexSum(expr.indices, body)
        self._isum_stack[temp] = expr
        return temp
