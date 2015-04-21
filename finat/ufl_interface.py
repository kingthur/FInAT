"""Provide interface functions which take UFL objects and return FInAT ones."""
import finat
import FIAT
import ufl

_cell_map = {
    "triangle": FIAT.reference_element.UFCTriangle(),
    "interval": FIAT.reference_element.UFCInterval()
}

_element_map = {
    "Lagrange": finat.Lagrange,
    "Discontinuous Lagrange": finat.DiscontinuousLagrange
}


def cell_from_ufl(cell):

    return _cell_map[cell.cellname()]


def element_from_ufl(element):

    # Need to handle the product cases.

    if isinstance(element, ufl.VectorElement):
        scalar_element = _element_map[element.family()](cell_from_ufl(element.cell()),
                                                        element.degree())
        # Note that UFL prepends the new dimension while FInAT appends it.
        return finat.VectorFiniteElement(scalar_element,
                                         element.value_shape()[0])
    else:
        return _element_map[element.family()](cell_from_ufl(element.cell()),
                                              element.degree())
