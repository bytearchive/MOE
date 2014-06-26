# -*- coding: utf-8 -*-
"""Test class for gp_hyper_opt view."""
import pyramid.testing

import simplejson as json

import testify as T


from moe.optimal_learning.python.constant import TEST_OPTIMIZATION_MULTISTARTS, TEST_GRADIENT_DESCENT_PARAMETERS, TEST_OPTIMIZATION_NUM_RANDOM_SAMPLES, TEST_EXPECTED_IMPROVEMENT_MC_ITERATIONS
from moe.tests.views.rest_gaussian_process_test_case import RestGaussianProcessTestCase
from moe.views.constant import GP_HYPER_OPT_MOE_ROUTE, GP_HYPER_OPT_PRETTY_ROUTE_NAME, GP_HYPER_OPT_ROUTE_NAME
from moe.views.rest.gp_hyper_opt import GpHyperOptResponse, GpHyperOptView
from moe.views.utils import _make_optimization_parameters_from_params


class TestGpHyperOptViews(RestGaussianProcessTestCase):

    """Test that the /gp/hyper_opt/* endpoints do the same thing as the C++ interface."""

    precompute_gaussian_process_data = True

    def _build_json_payload(self, domain, gaussian_process, covariance):
        """Create a json_payload to POST to the /gp/next_points/* endpoint with all needed info."""
        dict_to_dump = {
            'mc_iterations': TEST_EXPECTED_IMPROVEMENT_MC_ITERATIONS,
            'gp_historical_info': self._build_gp_historical_info(gaussian_process),
            'covariance_info': covariance.get_json_serializable_info(),
            'domain_info': domain.get_json_serializable_info(),
            'optimization_info': {
                'num_multistarts': TEST_OPTIMIZATION_MULTISTARTS,
                'num_random_samples': TEST_OPTIMIZATION_NUM_RANDOM_SAMPLES,
                'optimization_parameters': dict(TEST_GRADIENT_DESCENT_PARAMETERS._asdict()),
                },
            }

        hyper_dim = domain.dim + 1
        dict_to_dump['hyperparameter_domain_info'] = {
                'dim': hyper_dim,
                'domain_type': 'tensor_product',
                'domain_bounds': [],
                }

        for _ in range(hyper_dim):
            dict_to_dump['hyperparameter_domain_info']['domain_bounds'].append({
                'min': 0.1,
                'max': 2.0,
                })
        return json.dumps(dict_to_dump)

    def test_hyperparameters_passed_through(self):
        """Test that the hyperparameters get passed through to the endpoint."""
        test_case = self.gp_test_environments[0]

        python_domain, python_gp = test_case

        # Test default test parameters get passed through
        json_payload = json.loads(self._build_json_payload(python_domain, python_gp, python_gp._covariance))
        hyperparameter_domain_info = json_payload['hyperparameter_domain_info']

        request = pyramid.testing.DummyRequest(post=json_payload)
        request.json_body = json_payload
        view = GpHyperOptView(request)
        params = view.get_params_from_request()
        request_hyperparameters = params['hyperparameter_domain_info']
        
        T.assert_dicts_equal(params['hyperparameter_domain_info'], json_payload['hyperparameter_domain_info'])

        # Test arbitrary parameters get passed through
        json_payload['hyperparameter_domain_info']['domain_bounds'] = []
        for i in range(json_payload['hyperparameter_domain_info']['dim']):
            json_payload['hyperparameter_domain_info']['domain_bounds'].append({
                'min': 0.2*i,
                'max': 0.5*i,
                })
        
        request = pyramid.testing.DummyRequest(post=json_payload)
        request.json_body = json_payload
        view = GpHyperOptView(request)
        params = view.get_params_from_request()

        T.assert_dicts_equal(params['hyperparameter_domain_info'], json_payload['hyperparameter_domain_info'])

    def test_optimization_params_passed_through(self):
        """Test that the optimization parameters get passed through to the endpoint."""
        test_case = self.gp_test_environments[0]

        python_domain, python_gp = test_case

        # Test default test parameters get passed through
        json_payload = json.loads(self._build_json_payload(python_domain, python_gp, python_gp._covariance))

        request = pyramid.testing.DummyRequest(post=json_payload)
        request.json_body = json_payload
        view = GpHyperOptView(request)
        params = view.get_params_from_request()
        _, optimization_parameters, num_random_samples = _make_optimization_parameters_from_params(params)

        T.assert_equal(
                optimization_parameters.num_multistarts,
                TEST_OPTIMIZATION_MULTISTARTS
                )

        T.assert_equal(
                optimization_parameters._python_max_num_steps,
                TEST_GRADIENT_DESCENT_PARAMETERS.max_num_steps
                )

        # Test arbitrary parameters get passed through
        json_payload['optimization_info']['num_multistarts'] = TEST_OPTIMIZATION_MULTISTARTS + 5
        json_payload['optimization_info']['optimization_parameters']['max_num_steps'] = TEST_GRADIENT_DESCENT_PARAMETERS.max_num_steps + 10

        request = pyramid.testing.DummyRequest(post=json_payload)
        request.json_body = json_payload
        view = GpHyperOptView(request)
        params = view.get_params_from_request()
        _, optimization_parameters, num_random_samples = _make_optimization_parameters_from_params(params)

        T.assert_equal(
                optimization_parameters.num_multistarts,
                TEST_OPTIMIZATION_MULTISTARTS + 5
                )

        T.assert_equal(
                optimization_parameters._python_max_num_steps,
                TEST_GRADIENT_DESCENT_PARAMETERS.max_num_steps + 10
                )

    def test_interface_returns_same_as_cpp(self):
        """Test that the /gp/hyper_opt endpoint do the same thing as the C++ interface."""
        moe_route = GP_HYPER_OPT_MOE_ROUTE
        for test_case in self.gp_test_environments:
            python_domain, python_gp = test_case

            json_payload = self._build_json_payload(python_domain, python_gp, python_gp._covariance)
            resp = self.testapp.post(moe_route.endpoint, json_payload)
            resp_schema = GpHyperOptResponse()
            resp_dict = resp_schema.deserialize(json.loads(resp.body))

            T.assert_in('covariance_info', resp_dict)
            T.assert_equal(resp_dict['covariance_info']['covariance_type'], python_gp._covariance.covariance_type)
            # The optimal hyperparameters should be greater than zero
            for hyperparameter in resp_dict['covariance_info']['hyperparameters']:
                T.assert_gt(hyperparameter, 0.0)


if __name__ == "__main__":
    T.run()
