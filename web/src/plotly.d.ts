// plotly.js-dist-min ships without types. We use it only via
// react-plotly.js's factory, so a permissive any-typed shim is sufficient.
declare module "plotly.js-dist-min" {
  const Plotly: unknown;
  export default Plotly;
}
