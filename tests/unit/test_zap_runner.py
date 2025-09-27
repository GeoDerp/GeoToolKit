import json
from unittest.mock import MagicMock, patch

import requests
from src.models.finding import Finding
from src.orchestration.runners.zap_runner import ZapRunner

# Mock ZAP API responses for successful scan
MOCK_ZAP_SPIDER_STATUS_COMPLETE = '{"status": "100"}'
MOCK_ZAP_ASCAN_STATUS_COMPLETE = '{"status": "100"}'
MOCK_ZAP_ALERTS_OUTPUT = """
{
  "alerts": [
    {
      "alert": "Cross Site Scripting (Reflected)",
      "desc": "A reflected XSS vulnerability was found.",
      "solution": "Sanitize all user input.",
      "riskdesc": "High (Medium)",
      "cweid": "79",
      "instances": [
        {
          "uri": "http://localhost:8080/test?param=value",
          "method": "GET"
        }
      ]
    }
  ]
}
"""


def mock_requests_get(*args, **kwargs):
    url = args[0]
    if "spider/action/scan" in url:
        mock_response = MagicMock()
        mock_response.json.return_value = {"scan": "1"}
        mock_response.raise_for_status.return_value = None
        return mock_response
    elif "spider/view/status" in url:
        mock_response = MagicMock()
        mock_response.json.return_value = json.loads(MOCK_ZAP_SPIDER_STATUS_COMPLETE)
        mock_response.raise_for_status.return_value = None
        return mock_response
    elif "ascan/action/scan" in url:
        mock_response = MagicMock()
        mock_response.json.return_value = {"scan": "2"}
        mock_response.raise_for_status.return_value = None
        return mock_response
    elif "ascan/view/status" in url:
        mock_response = MagicMock()
        mock_response.json.return_value = json.loads(MOCK_ZAP_ASCAN_STATUS_COMPLETE)
        mock_response.raise_for_status.return_value = None
        return mock_response
    elif "core/view/alerts" in url:
        mock_response = MagicMock()
        mock_response.json.return_value = json.loads(MOCK_ZAP_ALERTS_OUTPUT)
        mock_response.raise_for_status.return_value = None
        return mock_response
    raise requests.exceptions.RequestException(f"Unexpected URL: {url}")


def test_zap_runner_success():
    with patch(
        "requests.get", side_effect=mock_requests_get
    ) as mock_requests_get_patch:
        findings = ZapRunner.run_scan("http://localhost:8080/target")

        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].tool == "OWASP ZAP"
        assert findings[0].severity == "High"
        assert "Cross Site Scripting" in findings[0].description
        expected_uri = json.loads(MOCK_ZAP_ALERTS_OUTPUT)["alerts"][0]["instances"][0][
            "uri"
        ]
        assert findings[0].filePath == expected_uri
        assert "CWE-79" in findings[0].complianceMappings


def test_zap_runner_connection_error(capsys):
    with patch(
        "requests.get", side_effect=requests.exceptions.ConnectionError
    ) as mock_requests_get_patch:
        findings = ZapRunner.run_scan("http://localhost:8080/target")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Error: Could not connect to ZAP" in captured.out


def test_zap_runner_request_exception(capsys):
    with patch(
        "requests.get",
        side_effect=requests.exceptions.RequestException("Test Request Error"),
    ) as mock_requests_get_patch:
        findings = ZapRunner.run_scan("http://localhost:8080/target")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Error interacting with ZAP API: Test Request Error" in captured.out


def test_zap_runner_json_decode_error(capsys):
    def mock_invalid_json_response(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_response.raise_for_status.return_value = None
        return mock_response

    with patch(
        "requests.get", side_effect=mock_invalid_json_response
    ) as mock_requests_get_patch:
        findings = ZapRunner.run_scan("http://localhost:8080/target")

        assert len(findings) == 0
        captured = capsys.readouterr()
        assert "Failed to decode ZAP API response" in captured.out
