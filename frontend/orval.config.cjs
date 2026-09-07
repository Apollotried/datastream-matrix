module.exports = {
  datastreamMatrix: {
    input: {
      target: './schema.yml',
    },
    output: {
      mode: 'split',
      target: './src/api/generated/datastream-matrix.ts',
      schemas: './src/api/generated/schemas',
      client: 'react-query',
      httpClient: 'fetch',
      baseUrl: '',
      clean: true,
      prettier: true,
      override: {
        mutator: {
          path: './src/api/mutator.ts',
          name: 'apiFetch',
        },
      },
    },
  },
};
