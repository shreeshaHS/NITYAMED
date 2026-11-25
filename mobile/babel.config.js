const path = require("path");

module.exports = function (api) {
  api.cache(true);
  const expoPreset = require.resolve("babel-preset-expo", {
    paths: [__dirname, path.join(__dirname, "node_modules", "expo")],
  });
  return {
    presets: [
      [expoPreset, { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
  };
};
