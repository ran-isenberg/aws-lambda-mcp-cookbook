def hld_prompt(design_requirements: str) -> str:
    prompt = f"""You are a serverless Python expert developing on AWS. Write comprehensive HLD  for the requirements '{design_requirements}'
The design should include:
- A clear description of the architecture
- Cost analysis
- Security considerations
- Scalability considerations
- Performance considerations
- Error handling and logging
- Monitoring and observability
- Deployment strategy
- Testing strategy
"""
    # Replace newlines with dots in the returned string
    return prompt.replace('\n', '.')
