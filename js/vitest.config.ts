// SPDX-License-Identifier: BSD-3-Clause

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      // 'lcov' (coverage/lcov.info) is what Codecov parses; without it the
      // `js` flag upload finds no machine-readable report and stays empty.
      reporter: ['text', 'html', 'lcov'],
    },
  },
});
