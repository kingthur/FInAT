import pytest
import FIAT
import finat
import numpy as np
from finat.ast import Variable


@pytest.fixture
def cell():
    return FIAT.reference_element.UFCTriangle()


@pytest.fixture
def lagrange(cell):
    return finat.Lagrange(cell, 1)


@pytest.fixture
def kernel_data(lagrange):
    vector_lagrange = finat.VectorFiniteElement(lagrange, 2)

    return finat.KernelData(vector_lagrange, Variable("X"))


@pytest.fixture
def context():
    return {'u': np.array([0.0, 0.6, 0.3])}


def quadrature(cell, degree):
    q = FIAT.quadrature.CollapsedQuadratureTriangleRule(cell, degree)

    points = finat.indices.PointIndex(finat.PointSet(q.get_points()))

    weights = finat.PointSet(q.get_weights())

    return points, weights


@pytest.mark.parametrize('degree', [1, 2, 3, 4, 5])
def test_basis_evaluation(cell, lagrange, kernel_data, degree):
    points, weights = quadrature(cell, degree)

    recipe = lagrange.basis_evaluation(points, kernel_data, derivative=None)

    result_finat = finat.interpreter.evaluate(recipe, {}, kernel_data)

    result_coffee = finat.coffee_compiler.evaluate(recipe, {}, kernel_data)

    assert(np.abs(result_finat - result_coffee) < 1.e-12).all()


@pytest.mark.parametrize('degree', [1, 2, 3, 4, 5])
def test_field_evaluation(cell, lagrange, kernel_data, context, degree):
    points, weights = quadrature(cell, degree)

    recipe = lagrange.field_evaluation(Variable("u"), points,
                                       kernel_data, derivative=None)

    result_finat = finat.interpreter.evaluate(recipe, context, kernel_data)

    result_coffee = finat.coffee_compiler.evaluate(recipe, context, kernel_data)

    assert(np.abs(result_finat - result_coffee) < 1.e-12).all()


@pytest.mark.parametrize('degree', [1, 2, 3, 4, 5])
def test_moment_evaluation(cell, lagrange, kernel_data, context, degree):
    points, weights = quadrature(cell, degree)

    f_recipe = lagrange.field_evaluation(Variable("u"), points,
                                         kernel_data, derivative=None)
    recipe = lagrange.moment_evaluation(f_recipe, weights, points,
                                        kernel_data, pullback=False)

    result_finat = finat.interpreter.evaluate(recipe, context, kernel_data)

    result_coffee = finat.coffee_compiler.evaluate(recipe, context, kernel_data)

    assert(np.abs(result_finat - result_coffee) < 1.e-12).all()