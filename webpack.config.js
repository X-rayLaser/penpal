const path = require('path');

module.exports = {
  mode: 'development',
  watchOptions: {
    poll: true,
    ignored: /node_modules/
  },
  entry: './frontend/src/index.js',
  output: {
    filename: 'main.js',
    path: path.resolve(__dirname, './frontend/public'),
  },
  module: {
    rules: [
      {
        test: /\.(?:js|mjs|cjs)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              ['@babel/preset-env', { targets: "defaults" }],
              ["@babel/preset-react"]
            ]
          }
        }
      }
    ]
  }
};