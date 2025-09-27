/**
 * Commitlint configuration for GeoToolKit
 * Using conventional commits with relaxed rules for better flexibility
 */
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Allow longer header for detailed commit messages
    'header-max-length': [2, 'always', 120],
    
    // Allow longer body lines for detailed explanations
    'body-max-line-length': [2, 'always', 120],
    
    // Allow empty subjects for merge commits and special cases
    'subject-empty': [1, 'never'],
    
    // Allow empty type for merge commits and special cases
    'type-empty': [1, 'never'],
    
    // Allow full stops in subjects
    'subject-full-stop': [0, 'never'],
    
    // Valid types for this project
    'type-enum': [
      2,
      'always',
      [
        'build',
        'chore',
        'ci',
        'docs',
        'feat',
        'fix',
        'perf',
        'refactor',
        'revert',
        'style',
        'test',
        'security',
        'deps',
        'config',
        'init',
        'rm'
      ]
    ],
    
    // Case rules
    'subject-case': [0, 'always'],
    'type-case': [2, 'always', 'lower-case'],
    
    // Allow certain patterns that are common in automated commits
    'footer-leading-blank': [1, 'always'],
    'body-leading-blank': [1, 'always']
  },
  
  // Custom parser options
  parserPreset: {
    parserOpts: {
      headerPattern: /^(\w*)(?:\((.*)\))?: (.*)$/,
      headerCorrespondence: ['type', 'scope', 'subject']
    }
  },
  
  // Ignore certain commit patterns (like merge commits)
  ignores: [
    (message) => message.includes('Merge'),
    (message) => message.includes('Co-authored-by:'),
    (message) => message.startsWith('Initial commit'),
    (message) => message.startsWith('feat(init): init'),
  ]
};