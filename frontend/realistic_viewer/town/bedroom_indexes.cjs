// CommonJS loads these JSON files in both the Node 20 CLI and the esbuild browser bundle.
module.exports = {
  surfaces: require("./materials/bedroom-sources.json"),
  publications: require("./bedroom_publications.json"),
};
