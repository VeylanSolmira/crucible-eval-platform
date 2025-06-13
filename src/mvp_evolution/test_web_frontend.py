#!/usr/bin/env python3
"""
Comprehensive tests for the web frontend component.
Run with: python test_web_frontend.py
"""

import unittest
import json
from unittest.mock import Mock, patch

from components import (
    WebFrontendService,
    SimpleHTMLFrontend,
    AdvancedHTMLFrontend,
    ReactFrontend,
    FrontendConfig,
    FrontendType,
    create_frontend,
    FrontendAPIIntegration
)


class TestFrontendConfig(unittest.TestCase):
    """Test FrontendConfig functionality"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = FrontendConfig()
        
        self.assertEqual(config.api_base_url, "/api")
        self.assertIsNone(config.websocket_url)
        self.assertTrue(config.enable_monitoring)
        self.assertTrue(config.enable_queue)
        self.assertEqual(config.theme, "default")
        self.assertTrue(config.features['async_execution'])
        
    def test_custom_config(self):
        """Test custom configuration"""
        config = FrontendConfig(
            api_base_url="/custom-api",
            theme="dark",
            features={'async_execution': False}
        )
        
        self.assertEqual(config.api_base_url, "/custom-api")
        self.assertEqual(config.theme, "dark")
        self.assertFalse(config.features['async_execution'])
        
    def test_config_json_serialization(self):
        """Test configuration JSON serialization"""
        config = FrontendConfig(api_base_url="/test")
        json_str = config.to_json()
        data = json.loads(json_str)
        
        self.assertEqual(data['apiBaseUrl'], "/test")
        self.assertTrue(data['enableMonitoring'])
        self.assertIn('features', data)


class TestSimpleHTMLFrontend(unittest.TestCase):
    """Test SimpleHTMLFrontend implementation"""
    
    def setUp(self):
        self.frontend = SimpleHTMLFrontend()
        
    def test_html_generation(self):
        """Test HTML generation"""
        html = self.frontend.get_index_html()
        
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<title>Crucible Platform - Simple Edition</title>', html)
        self.assertIn('textarea', html)
        self.assertIn('runEval()', html)
        
    def test_security_warning_toggle(self):
        """Test security warning can be toggled"""
        # With warnings
        frontend_with_warnings = SimpleHTMLFrontend()
        html = frontend_with_warnings.get_index_html()
        self.assertIn('SAFETY WARNING', html)
        
        # Without warnings
        config = FrontendConfig(features={'security_warnings': False})
        frontend_no_warnings = SimpleHTMLFrontend(config)
        html = frontend_no_warnings.get_index_html()
        self.assertNotIn('SAFETY WARNING', html)
        
    def test_api_endpoint_configuration(self):
        """Test API endpoint is configurable"""
        config = FrontendConfig(api_base_url="/custom-api")
        frontend = SimpleHTMLFrontend(config)
        html = frontend.get_index_html()
        
        self.assertIn('config.api_base_url + \'/eval\'', html)
        self.assertIn('/custom-api', html)
        
    def test_no_assets(self):
        """Test simple frontend has no assets"""
        result = self.frontend.get_asset('any-file.css')
        self.assertIsNone(result)
        
    def test_self_test(self):
        """Test self-test functionality"""
        results = self.frontend.self_test()
        
        self.assertTrue(results['passed'])
        self.assertIn('tests', results)
        self.assertTrue(len(results['tests']) > 0)


class TestAdvancedHTMLFrontend(unittest.TestCase):
    """Test AdvancedHTMLFrontend implementation"""
    
    def setUp(self):
        self.frontend = AdvancedHTMLFrontend()
        
    def test_html_generation(self):
        """Test HTML generation with advanced features"""
        html = self.frontend.get_index_html()
        
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<title>Crucible Platform - Advanced Edition</title>', html)
        self.assertIn('Queue Status', html)
        self.assertIn('Real-time Event Stream', html)
        self.assertIn('submitEvaluation()', html)
        
    def test_feature_list_generation(self):
        """Test feature list adapts to configuration"""
        # Full features
        html = self.frontend.get_index_html()
        self.assertIn('Queue-based execution', html)
        self.assertIn('Real-time monitoring', html)
        
        # Limited features
        config = FrontendConfig(enable_queue=False, enable_monitoring=False)
        limited_frontend = AdvancedHTMLFrontend(config)
        html = limited_frontend.get_index_html()
        
        # Should still show some features
        self.assertIn('Security isolation', html)
        
    def test_batch_submission_toggle(self):
        """Test batch submission can be toggled"""
        # With batch
        html = self.frontend.get_index_html()
        self.assertIn('Submit 5 Evaluations', html)
        
        # Without batch
        config = FrontendConfig(features={'batch_submission': False})
        frontend = AdvancedHTMLFrontend(config)
        html = frontend.get_index_html()
        self.assertNotIn('Submit 5 Evaluations', html)
        
    def test_monitoring_panel_toggle(self):
        """Test monitoring panel can be disabled"""
        # With monitoring
        html = self.frontend.get_index_html()
        self.assertIn('Real-time Event Stream', html)
        
        # Without monitoring
        config = FrontendConfig(enable_monitoring=False)
        frontend = AdvancedHTMLFrontend(config)
        html = frontend.get_index_html()
        self.assertIn('Monitoring disabled', html)
        
    def test_javascript_features(self):
        """Test JavaScript adapts to features"""
        html = self.frontend.get_index_html()
        
        # Check for async features
        self.assertIn('eval-async', html)
        self.assertIn('activeEvaluations', html)
        self.assertIn('updateStatus', html)
        
    def test_customization(self):
        """Test runtime customization"""
        self.frontend.customize({
            'theme': 'custom-theme',
            'api_base_url': '/new-api'
        })
        
        self.assertEqual(self.frontend.config.theme, 'custom-theme')
        self.assertEqual(self.frontend.config.api_base_url, '/new-api')
        
        # Check it affects output
        html = self.frontend.get_index_html()
        self.assertIn('/new-api', html)


class TestFrontendFactory(unittest.TestCase):
    """Test frontend factory function"""
    
    def test_create_simple_frontend(self):
        """Test creating simple frontend"""
        frontend = create_frontend(FrontendType.SIMPLE_HTML)
        self.assertIsInstance(frontend, SimpleHTMLFrontend)
        
    def test_create_advanced_frontend(self):
        """Test creating advanced frontend"""
        frontend = create_frontend(FrontendType.ADVANCED_HTML)
        self.assertIsInstance(frontend, AdvancedHTMLFrontend)
        
    def test_create_react_frontend(self):
        """Test creating React frontend (placeholder)"""
        frontend = create_frontend(FrontendType.REACT)
        self.assertIsInstance(frontend, ReactFrontend)
        
        # Check it returns valid HTML
        html = frontend.get_index_html()
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('root', html)
        self.assertIn('CRUCIBLE_CONFIG', html)
        
        
    def test_create_with_config(self):
        """Test creating frontend with custom config"""
        config = FrontendConfig(theme="test-theme")
        frontend = create_frontend(FrontendType.SIMPLE_HTML, config)
        
        self.assertEqual(frontend.config.theme, "test-theme")
        
    def test_invalid_frontend_type(self):
        """Test invalid frontend type raises error"""
        with self.assertRaises(ValueError):
            create_frontend("invalid-type")


class TestFrontendAPIIntegration(unittest.TestCase):
    """Test frontend and API integration"""
    
    def setUp(self):
        self.frontend = Mock(spec=WebFrontendService)
        self.api_service = Mock()
        self.integration = FrontendAPIIntegration(self.frontend, self.api_service)
        
    def test_route_registration(self):
        """Test routes are registered with API"""
        # Check that routes were added
        calls = self.api_service.add_route.call_args_list
        
        # Should register at least 3 routes
        self.assertGreaterEqual(len(calls), 3)
        
        # Check specific routes
        routes = [(call[0][0], call[0][1]) for call in calls]
        self.assertIn(('GET', '/'), routes)
        self.assertIn(('GET', '/config.json'), routes)
        self.assertIn(('GET', '/assets/*'), routes)
        
    def test_asset_serving(self):
        """Test asset serving through integration"""
        # Mock frontend asset response
        self.frontend.get_asset.return_value = (b'test-content', 'text/css')
        
        # Create mock request
        request = Mock()
        request.path = '/assets/styles.css'
        
        # Get the asset handler
        asset_handler = self.api_service.add_route.call_args_list[2][0][2]
        result = asset_handler(request)
        
        self.assertEqual(result['body'], b'test-content')
        self.assertEqual(result['headers']['Content-Type'], 'text/css')
        
    def test_asset_not_found(self):
        """Test 404 for missing assets"""
        # Mock no asset found
        self.frontend.get_asset.return_value = None
        
        # Create mock request
        request = Mock()
        request.path = '/assets/missing.js'
        
        # Get the asset handler
        asset_handler = self.api_service.add_route.call_args_list[2][0][2]
        result = asset_handler(request)
        
        self.assertEqual(result['status'], 404)


class TestWebFrontendComponent(unittest.TestCase):
    """Integration tests for the entire web frontend component"""
    
    def test_component_lifecycle(self):
        """Test component creation, customization, and usage"""
        # Create frontend
        config = FrontendConfig(theme="light")
        frontend = create_frontend(FrontendType.ADVANCED_HTML, config)
        
        # Test initial state
        self.assertEqual(frontend.config.theme, "light")
        html = frontend.get_index_html()
        self.assertIn('Advanced Edition', html)
        
        # Customize
        frontend.customize({
            'theme': 'dark',
            'features': {'batch_submission': False}
        })
        
        # Test customized state
        self.assertEqual(frontend.config.theme, "dark")
        self.assertFalse(frontend.config.features['batch_submission'])
        
        # Get configuration
        config_json = frontend.get_config()
        config_data = json.loads(config_json)
        self.assertEqual(config_data['theme'], 'dark')
        
    def test_all_frontends_testable(self):
        """Test all frontend types are testable"""
        frontend_types = [
            FrontendType.SIMPLE_HTML,
            FrontendType.ADVANCED_HTML,
            FrontendType.REACT
        ]
        
        for frontend_type in frontend_types:
            frontend = create_frontend(frontend_type)
            
            # Should have self-test
            results = frontend.self_test()
            self.assertIn('passed', results)
            self.assertIn('tests', results)
            
            # Should have test suite
            suite = frontend.get_test_suite()
            self.assertIsInstance(suite, unittest.TestSuite)
            self.assertGreater(suite.countTestCases(), 0)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)