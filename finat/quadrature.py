from __future__ import absolute_import, print_function, division
from six import with_metaclass

from abc import ABCMeta, abstractproperty
from functools import reduce

import numpy

import gem
from gem.utils import cached_property

from FIAT.reference_element import QUADRILATERAL, TENSORPRODUCT
# from FIAT.quadrature import compute_gauss_jacobi_rule as gauss_jacobi_rule
from FIAT.quadrature_schemes import create_quadrature as fiat_scheme

from finat.point_set import PointSet, TensorPointSet


def make_quadrature(ref_el, degree, scheme="default"):
    """
    Generate quadrature rule for given reference element
    that will integrate an polynomial of order 'degree' exactly.

    For low-degree (<=6) polynomials on triangles and tetrahedra, this
    uses hard-coded rules, otherwise it falls back to a collapsed
    Gauss scheme on simplices.  On tensor-product cells, it is a
    tensor-product quadrature rule of the subcells.

    :arg cell: The FIAT cell to create the quadrature for.
    :arg degree: The degree of polynomial that the rule should
        integrate exactly.
    """
    if ref_el.get_shape() == TENSORPRODUCT:
        try:
            degree = tuple(degree)
        except TypeError:
            degree = (degree,) * len(ref_el.cells)

        assert len(ref_el.cells) == len(degree)
        quad_rules = [make_quadrature(c, d, scheme)
                      for c, d in zip(ref_el.cells, degree)]
        return TensorProductQuadratureRule(quad_rules)

    if ref_el.get_shape() == QUADRILATERAL:
        return make_quadrature(ref_el.product, degree, scheme)

    if degree < 0:
        raise ValueError("Need positive degree, not %d" % degree)

    fiat_rule = fiat_scheme(ref_el, degree, scheme)
    return QuadratureRule(fiat_rule.get_points(), fiat_rule.get_weights())


class AbstractQuadratureRule(with_metaclass(ABCMeta)):
    """Abstract class representing a quadrature rule as point set and a
    corresponding set of weights."""

    @abstractproperty
    def point_set(self):
        """Point set object representing the quadrature points."""

    @abstractproperty
    def weight_expression(self):
        """GEM expression describing the weights, with the same free indices
        as the point set."""


class QuadratureRule(AbstractQuadratureRule):
    """Generic quadrature rule with no internal structure."""

    def __init__(self, points, weights):
        weights = numpy.asarray(weights)
        assert len(points) == len(weights)

        self._points = numpy.asarray(points)
        self.weights = numpy.asarray(weights)

    @cached_property
    def point_set(self):
        return PointSet(self._points)

    @cached_property
    def weight_expression(self):
        return gem.Indexed(gem.Literal(self.weights), self.point_set.indices)


class TensorProductQuadratureRule(AbstractQuadratureRule):
    """Quadrature rule which is a tensor product of other rules."""

    def __init__(self, factors):
        self.factors = tuple(factors)

    @cached_property
    def point_set(self):
        return TensorPointSet(q.point_set for q in self.factors)

    @cached_property
    def weight_expression(self):
        return reduce(gem.Product, (q.weight_expression for q in self.factors))
