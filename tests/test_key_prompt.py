from nvai.key_prompt import normalize_base_url


def test_normalize_plain_host_adds_https():
    assert normalize_base_url("integrate.api.nvidia.com/v1") == "https://integrate.api.nvidia.com/v1"


def test_normalize_slack_link_format():
    value = "<https://integrate.api.nvidia.com/v1|integrate.api.nvidia.com/v1>"
    assert normalize_base_url(value) == "https://integrate.api.nvidia.com/v1"


def test_normalize_parenthesized_url_format():
    value = "integrate.api.nvidia.com/v1 (https://integrate.api.nvidia.com/v1)"
    assert normalize_base_url(value) == "https://integrate.api.nvidia.com/v1"
