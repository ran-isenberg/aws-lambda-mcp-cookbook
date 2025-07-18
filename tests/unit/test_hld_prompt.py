from service.logic.prompts.hld import hld_prompt


def test_hld_prompt():
    """Test that hld_prompt works correctly with various inputs."""
    design_requirements = 'Build a REST API'
    result = hld_prompt(design_requirements)

    # Should return a string
    assert isinstance(result, str)

    # Should include the design requirements
    assert design_requirements in result

    # Should replace newlines with dots
    assert '\n' not in result

    # Should contain expected sections
    expected_sections = [
        'architecture',
        'Cost analysis',
        'Security considerations',
        'Scalability considerations',
        'Performance considerations',
        'Error handling and logging',
        'Monitoring and observability',
        'Deployment strategy',
        'Testing strategy',
    ]
    for section in expected_sections:
        assert section in result

    # Should start with expected text
    assert result.startswith('You are a serverless Python expert developing on AWS')
