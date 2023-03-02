#!/usr/bin/env python3
# Copyright 2010-2022 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for ModelBuilder."""

import math
import numpy as np
import numpy.testing as np_testing
import os

from ortools.linear_solver.python import model_builder as mb
import unittest


class ModelBuilderTest(unittest.TestCase):
    # Number of decimal places to use for numerical tolerance for
    # checking primal, dual, objective values and other values.
    NUM_PLACES = 5

    # pylint: disable=too-many-statements
    def run_minimal_linear_example(self, solver_name):
        """Minimal Linear Example."""
        model = mb.ModelBuilder()
        model.name = 'minimal_linear_example'
        x1 = model.new_num_var(0.0, math.inf, 'x1')
        x2 = model.new_num_var(0.0, math.inf, 'x2')
        x3 = model.new_num_var(0.0, math.inf, 'x3')
        self.assertEqual(3, model.num_variables)
        self.assertFalse(x1.is_integral)
        self.assertEqual(0.0, x1.lower_bound)
        self.assertEqual(math.inf, x2.upper_bound)
        x1.lower_bound = 1.0
        self.assertEqual(1.0, x1.lower_bound)

        model.maximize(10.0 * x1 + 6 * x2 + 4.0 * x3 - 3.5)
        self.assertEqual(4.0, x3.objective_coefficient)
        self.assertEqual(-3.5, model.objective_offset)
        model.objective_offset = -5.5
        self.assertEqual(-5.5, model.objective_offset)

        c0 = model.add(x1 + x2 + x3 <= 100.0)
        self.assertEqual(100, c0.upper_bound)
        c1 = model.add(10 * x1 + 4.0 * x2 + 5.0 * x3 <= 600.0, 'c1')
        self.assertEqual('c1', c1.name)
        c2 = model.add(2.0 * x1 + 2.0 * x2 + 6.0 * x3 <= 300.0)
        self.assertEqual(-math.inf, c2.lower_bound)

        solver = mb.ModelSolver(solver_name)
        self.assertEqual(mb.SolveStatus.OPTIMAL, solver.solve(model))

        # The problem has an optimal solution.
        self.assertAlmostEqual(733.333333 + model.objective_offset,
                               solver.objective_value,
                               places=self.NUM_PLACES)
        self.assertAlmostEqual(
            solver.value(10.0 * x1 + 6 * x2 + 4.0 * x3 - 5.5),
            solver.objective_value,
            places=self.NUM_PLACES,
        )
        self.assertAlmostEqual(33.333333,
                               solver.value(x1),
                               places=self.NUM_PLACES)
        self.assertAlmostEqual(66.666667,
                               solver.value(x2),
                               places=self.NUM_PLACES)
        self.assertAlmostEqual(0.0, solver.value(x3), places=self.NUM_PLACES)

        dual_objective_value = (solver.dual_value(c0) * c0.upper_bound +
                                solver.dual_value(c1) * c1.upper_bound +
                                solver.dual_value(c2) * c2.upper_bound +
                                model.objective_offset)
        self.assertAlmostEqual(solver.objective_value,
                               dual_objective_value,
                               places=self.NUM_PLACES)

        # x1 and x2 are basic
        self.assertAlmostEqual(0.0,
                               solver.reduced_cost(x1),
                               places=self.NUM_PLACES)
        self.assertAlmostEqual(0.0,
                               solver.reduced_cost(x2),
                               places=self.NUM_PLACES)
        # x3 is non-basic
        x3_expected_reduced_cost = (4.0 - 1.0 * solver.dual_value(c0) -
                                    5.0 * solver.dual_value(c1))
        self.assertAlmostEqual(x3_expected_reduced_cost,
                               solver.reduced_cost(x3),
                               places=self.NUM_PLACES)

        self.assertIn('minimal_linear_example',
                      model.export_to_lp_string(False))
        self.assertIn('minimal_linear_example',
                      model.export_to_mps_string(False))

    def test_minimal_linear_example(self):
        self.run_minimal_linear_example('glop')

    def test_import_from_mps_string(self):
        mps_data = """
* Generated by MPModelProtoExporter
*   Name             : SupportedMaximizationProblem
*   Format           : Free
*   Constraints      : 0
*   Variables        : 1
*     Binary         : 0
*     Integer        : 0
*     Continuous     : 1
NAME          SupportedMaximizationProblem
OBJSENSE
  MAX
ROWS
 N  COST
COLUMNS
    X_ONE   COST         1
BOUNDS
 UP BOUND   X_ONE        4
ENDATA
"""
        model = mb.ModelBuilder()
        self.assertTrue(model.import_from_mps_string(mps_data))
        self.assertEqual(model.name, 'SupportedMaximizationProblem')

    def test_import_from_mps_file(self):
        path = os.path.dirname(__file__)
        mps_path = f'{path}/../testdata/maximization.mps'
        model = mb.ModelBuilder()
        self.assertTrue(model.import_from_mps_file(mps_path))
        self.assertEqual(model.name, 'SupportedMaximizationProblem')

    def test_import_from_lp_string(self):
        lp_data = """
      min: x + y;
      bin: b1, b2, b3;
      1 <= x <= 42;
      constraint_num1: 5 b1 + 3b2 + x <= 7;
      4 y + b2 - 3 b3 <= 2;
      constraint_num2: -4 b1 + b2 - 3 z <= -2;
"""
        model = mb.ModelBuilder()
        self.assertTrue(model.import_from_lp_string(lp_data))
        self.assertEqual(6, model.num_variables)
        self.assertEqual(3, model.num_constraints)
        self.assertEqual(1, model.var_from_index(0).lower_bound)
        self.assertEqual(42, model.var_from_index(0).upper_bound)
        self.assertEqual('x', model.var_from_index(0).name)

    def test_import_from_lp_file(self):
        path = os.path.dirname(__file__)
        lp_path = f'{path}/../testdata/small_model.lp'
        model = mb.ModelBuilder()
        self.assertTrue(model.import_from_lp_file(lp_path))
        self.assertEqual(6, model.num_variables)
        self.assertEqual(3, model.num_constraints)
        self.assertEqual(1, model.var_from_index(0).lower_bound)
        self.assertEqual(42, model.var_from_index(0).upper_bound)
        self.assertEqual('x', model.var_from_index(0).name)

    def test_class_api(self):
        model = mb.ModelBuilder()
        x = model.new_int_var(0, 10, 'x')
        y = model.new_int_var(1, 10, 'y')
        z = model.new_int_var(2, 10, 'z')
        t = model.new_int_var(3, 10, 't')

        e1 = mb.LinearExpr.sum([x, y, z])
        expected_vars = np.array([0, 1, 2], dtype=np.int32)
        np_testing.assert_array_equal(expected_vars, e1.variable_indices)
        np_testing.assert_array_equal(np.array([1, 1, 1], dtype=np.double),
                                      e1.coefficients)
        self.assertEqual(e1.constant, 0.0)
        self.assertEqual(e1.pretty_string(model.helper), 'x + y + z')

        e2 = mb.LinearExpr.sum([e1, 4.0])
        np_testing.assert_array_equal(expected_vars, e2.variable_indices)
        np_testing.assert_array_equal(np.array([1, 1, 1], dtype=np.double),
                                      e2.coefficients)
        self.assertEqual(e2.constant, 4.0)
        self.assertEqual(e2.pretty_string(model.helper), 'x + y + z + 4.0')

        e3 = mb.LinearExpr.term(e2, 2)
        np_testing.assert_array_equal(expected_vars, e3.variable_indices)
        np_testing.assert_array_equal(np.array([2, 2, 2], dtype=np.double),
                                      e3.coefficients)
        self.assertEqual(e3.constant, 8.0)
        self.assertEqual(e3.pretty_string(model.helper),
                         '2.0 * x + 2.0 * y + 2.0 * z + 8.0')

        e4 = mb.LinearExpr.weighted_sum([x, t], [-1, 1], constant=2)
        np_testing.assert_array_equal(np.array([0, 3], dtype=np.int32),
                                      e4.variable_indices)
        np_testing.assert_array_equal(np.array([-1, 1], dtype=np.double),
                                      e4.coefficients)
        self.assertEqual(e4.constant, 2.0)
        self.assertEqual(e4.pretty_string(model.helper), '-x + t + 2.0')

        e4b = e4 * 3.0
        np_testing.assert_array_equal(np.array([0, 3], dtype=np.int32),
                                      e4b.variable_indices)
        np_testing.assert_array_equal(np.array([-3, 3], dtype=np.double),
                                      e4b.coefficients)
        self.assertEqual(e4b.constant, 6.0)
        self.assertEqual(e4b.pretty_string(model.helper),
                         '-3.0 * x + 3.0 * t + 6.0')

        e5 = mb.LinearExpr.sum([e1, -3, e4])
        np_testing.assert_array_equal(np.array([0, 1, 2, 0, 3], dtype=np.int32),
                                      e5.variable_indices)
        np_testing.assert_array_equal(
            np.array([1, 1, 1, -1, 1], dtype=np.double), e5.coefficients)
        self.assertEqual(e5.constant, -1.0)
        self.assertEqual(e5.pretty_string(model.helper),
                         'x + y + z - x + t - 1.0')

        e6 = mb.LinearExpr.term(x, 2.0, constant=1.0)
        np_testing.assert_array_equal(np.array([0], dtype=np.int32),
                                      e6.variable_indices)
        np_testing.assert_array_equal(np.array([2], dtype=np.double),
                                      e6.coefficients)
        self.assertEqual(e6.constant, 1.0)

        e7 = mb.LinearExpr.term(x, 1.0, constant=0.0)
        self.assertEqual(x, e7)

        e8 = mb.LinearExpr.term(2, 3, constant=4)
        self.assertEqual(e8, 10)

    def test_variables(self):
        model = mb.ModelBuilder()
        x = model.new_int_var(0.0, 4.0, 'x')
        self.assertEqual(0, x.index)
        self.assertEqual(0.0, x.lower_bound)
        self.assertEqual(4.0, x.upper_bound)
        self.assertEqual('x', x.name)
        x.lower_bound = 1.0
        x.upper_bound = 3.0
        self.assertEqual(1.0, x.lower_bound)
        self.assertEqual(3.0, x.upper_bound)
        self.assertTrue(x.is_integral)

        # Tests the equality operator.
        y = model.new_int_var(0.0, 4.0, 'y')
        x_copy = model.var_from_index(0)
        self.assertEqual(x, x)
        self.assertEqual(x, x_copy)
        self.assertNotEqual(x, y)

        # array
        xs = model.new_int_var_array(shape=10,
                                     lower_bounds=0.0,
                                     upper_bounds=5.0,
                                     name='xs_')
        self.assertEqual(10, xs.size)
        self.assertEqual('xs_4', str(xs[4]))
        lbs = np.array([1.0, 2.0, 3.0])
        ubs = [3.0, 4.0, 5.0]
        ys = model.new_int_var_array(lower_bounds=lbs,
                                     upper_bounds=ubs,
                                     name='ys_')
        self.assertEqual('VariableContainer([12 13 14])', str(ys))
        zs = model.new_int_var_array(lower_bounds=[1.0, 2.0, 3],
                                     upper_bounds=[4, 4, 4],
                                     name='zs_')
        self.assertEqual(3, zs.size)
        self.assertEqual((3,), zs.shape)
        self.assertEqual('zs_1', str(zs[1]))
        self.assertEqual('zs_2(index=17, lb=3.0, ub=4.0, integer)', repr(zs[2]))
        self.assertTrue(zs[2].is_integral)

        bs = model.new_bool_var_array([4, 5], 'bs_')
        self.assertEqual((4, 5), bs.shape)
        self.assertEqual((5, 4), bs.T.shape)
        self.assertEqual(31, bs.index_at((2, 3)))
        self.assertEqual(20, bs.size)
        self.assertEqual((20,), bs.flatten().shape)
        self.assertTrue(bs[1, 1].is_integral)

        # Slices are [lb, ub) closed - open.
        self.assertEqual(5, bs[3, :].size)
        self.assertEqual(6, bs[1:3, 2:5].size)

        sum_bs = np.sum(bs)
        self.assertEqual(20, sum_bs.variable_indices.size)
        np_testing.assert_array_equal(sum_bs.variable_indices,
                                      bs.variable_indices.flatten())
        np_testing.assert_array_equal(sum_bs.coefficients, np.ones(20))

        sum_bs_cte = np.sum(bs, 2.2)
        self.assertEqual(20, sum_bs_cte.variable_indices.size)
        np_testing.assert_array_equal(sum_bs_cte.variable_indices,
                                      bs.variable_indices.flatten())
        np_testing.assert_array_equal(sum_bs.coefficients, np.ones(20))
        self.assertEqual(sum_bs_cte.constant, 2.2)

        times_bs = np.dot(bs[1], 4)
        np_testing.assert_array_equal(times_bs.variable_indices,
                                      bs[1].variable_indices.flatten())
        np_testing.assert_array_equal(times_bs.coefficients, np.full(5, 4.0))

        times_bs_rev = np.dot(4, bs[2])
        np_testing.assert_array_equal(times_bs_rev.variable_indices,
                                      bs[2].variable_indices.flatten())
        np_testing.assert_array_equal(times_bs_rev.coefficients,
                                      np.full(5, 4.0))

        dot_bs = np.dot(bs[2], np.array([1, 2, 3, 4, 5], dtype=np.double))
        np_testing.assert_array_equal(dot_bs.variable_indices,
                                      bs[2].variable_indices)
        np_testing.assert_array_equal(dot_bs.coefficients, [1, 2, 3, 4, 5])

        # Tests the hash method.
        var_set = set()
        var_set.add(x)
        self.assertIn(x, var_set)
        self.assertIn(x_copy, var_set)
        self.assertNotIn(y, var_set)

    def test_numpy_var_arrays(self):
        model = mb.ModelBuilder()

        x = model.new_var_array(
            lower_bounds=0.0,
            upper_bounds=4.0,
            shape=[2, 3],
            is_integral=False,
        )
        np_testing.assert_array_equal(x.shape, [2, 3])

        y = model.new_var_array(
            lower_bounds=[[0.0, 1.0, 2.0], [0.0, 0.0, 2.0]],
            upper_bounds=4.0,
            is_integral=False,
            name='y',
        )
        np_testing.assert_array_equal(y.shape, [2, 3])

        z = model.new_var_array(
            lower_bounds=0.0,
            upper_bounds=[[2.0, 1.0, 2.0], [3.0, 4.0, 2.0]],
            is_integral=False,
            name='z',
        )
        np_testing.assert_array_equal(z.shape, [2, 3])

        with self.assertRaises(ValueError):
            x = model.new_var_array(
                lower_bounds=0.0,
                upper_bounds=4.0,
                is_integral=False,
            )

        with self.assertRaises(ValueError):
            x = model.new_var_array(
                lower_bounds=[0, 0],
                upper_bounds=[1, 2, 3],
                is_integral=False,
            )

        with self.assertRaises(ValueError):
            x = model.new_var_array(
                shape=[2, 3],
                lower_bounds=0.0,
                upper_bounds=[1, 2, 3],
                is_integral=False,
            )

        with self.assertRaises(ValueError):
            x = model.new_var_array(
                shape=[2, 3],
                lower_bounds=[1, 2],
                upper_bounds=4.0,
                is_integral=False,
            )

        with self.assertRaises(ValueError):
            x = model.new_var_array(
                shape=[2, 3],
                lower_bounds=0.0,
                upper_bounds=4.0,
                is_integral=[False, True],
            )

        with self.assertRaises(ValueError):
            x = model.new_var_array(
                lower_bounds=[1, 2],
                upper_bounds=4.0,
                is_integral=[False, False, False],
            )

    def test_numpy_num_var_arrays(self):
        model = mb.ModelBuilder()

        x = model.new_num_var_array(
            lower_bounds=0.0,
            upper_bounds=4.0,
            shape=[2, 3],
        )
        np_testing.assert_array_equal(x.shape, [2, 3])

        y = model.new_num_var_array(
            lower_bounds=[[0.0, 1.0, 2.0], [0.0, 0.0, 2.0]],
            upper_bounds=4.0,
            name='y',
        )
        np_testing.assert_array_equal(y.shape, [2, 3])

        z = model.new_num_var_array(
            lower_bounds=0.0,
            upper_bounds=[[2.0, 1.0, 2.0], [3.0, 4.0, 2.0]],
            name='z',
        )
        np_testing.assert_array_equal(z.shape, [2, 3])

        with self.assertRaises(ValueError):
            x = model.new_num_var_array(
                lower_bounds=0.0,
                upper_bounds=4.0,
            )

        with self.assertRaises(ValueError):
            x = model.new_num_var_array(
                lower_bounds=[0, 0],
                upper_bounds=[1, 2, 3],
            )

        with self.assertRaises(ValueError):
            x = model.new_num_var_array(
                shape=[2, 3],
                lower_bounds=0.0,
                upper_bounds=[1, 2, 3],
            )

        with self.assertRaises(ValueError):
            x = model.new_num_var_array(
                shape=[2, 3],
                lower_bounds=[1, 2],
                upper_bounds=4.0,
            )

    def test_numpy_int_var_arrays(self):
        model = mb.ModelBuilder()

        x = model.new_int_var_array(
            lower_bounds=0.0,
            upper_bounds=4.0,
            shape=[2, 3],
        )
        np_testing.assert_array_equal(x.shape, [2, 3])

        y = model.new_int_var_array(
            lower_bounds=[[0.0, 1.0, 2.0], [0.0, 0.0, 2.0]],
            upper_bounds=4.0,
            name='y',
        )
        np_testing.assert_array_equal(y.shape, [2, 3])

        z = model.new_int_var_array(
            lower_bounds=0.0,
            upper_bounds=[[2.0, 1.0, 2.0], [3.0, 4.0, 2.0]],
            name='z',
        )
        np_testing.assert_array_equal(z.shape, [2, 3])

        with self.assertRaises(ValueError):
            x = model.new_int_var_array(
                lower_bounds=0.0,
                upper_bounds=4.0,
            )

        with self.assertRaises(ValueError):
            x = model.new_int_var_array(
                lower_bounds=[0, 0],
                upper_bounds=[1, 2, 3],
            )

        with self.assertRaises(ValueError):
            x = model.new_int_var_array(
                shape=[2, 3],
                lower_bounds=0.0,
                upper_bounds=[1, 2, 3],
            )

        with self.assertRaises(ValueError):
            x = model.new_int_var_array(
                shape=[2, 3],
                lower_bounds=[1, 2],
                upper_bounds=4.0,
            )

    def test_duplicate_variables(self):
        model = mb.ModelBuilder()
        x = model.new_int_var(0.0, 4.0, 'x')
        y = model.new_int_var(0.0, 4.0, 'y')
        z = model.new_int_var(0.0, 4.0, 'z')
        model.add(x + 2 * y == x - z)
        model.minimize(x + y + z)
        solver = mb.ModelSolver('scip')
        self.assertEqual(mb.SolveStatus.OPTIMAL, solver.solve(model))

    def test_issue_3614(self):
        total_number_of_choices = 5 + 1
        total_unique_products = 3
        standalone_features = list(range(5))
        feature_bundle_incidence_matrix = {}
        for idx in range(len(standalone_features)):
            feature_bundle_incidence_matrix[idx, 0] = 0
        feature_bundle_incidence_matrix[0, 0] = 1
        feature_bundle_incidence_matrix[1, 0] = 1

        bundle_start_idx = len(standalone_features)
        # Model
        model = mb.ModelBuilder()
        y = {}
        v = {}
        for i in range(total_number_of_choices):
            y[i] = model.new_bool_var(f'y_{i}')

        for j in range(total_unique_products):
            for i in range(len(standalone_features)):
                v[i, j] = model.new_bool_var(f'v_{(i,j)}')
                model.add(v[i, j] == (y[i] +
                                      (feature_bundle_incidence_matrix[(i, 0)] *
                                       y[bundle_start_idx])))

        solver = mb.ModelSolver('scip')
        status = solver.solve(model)
        self.assertEqual(mb.SolveStatus.OPTIMAL, status)

    def test_varcompvar(self):
        model = mb.ModelBuilder()
        x = model.new_int_var(0.0, 4.0, 'x')
        y = model.new_int_var(0.0, 4.0, 'y')
        ct = x == y
        self.assertEqual(ct.left.index, x.index)
        self.assertEqual(ct.right.index, y.index)


if __name__ == '__main__':
    unittest.main()
