# API Contracts for Automated Malicious Code Scanner

This directory will contain the API contracts for the toolkit, defined using a format like OpenAPI or JSON Schema. These contracts will define the structure of the input and output data for the workflow.

For example, the input to the workflow could be a JSON file with the following structure:

```json
{
  "projects": [
    {
      "url": "https://github.com/example/project1"
    },
    {
      "url": "https://github.com/example/project2"
    }
  ]
}
```

The output report could also be a JSON file, following the structure defined in the data model.
