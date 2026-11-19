import Icon from "./Icon";
import packageInfo from "../../package.json";

/** Version of the frontend visible to users, sourced from its package manifest. */
export const APP_VERSION = packageInfo.version;

export default function Brand() {
  return <span className="nf-brand">
    <span className="nf-brand-mark"><Icon name="leaf"/></span>
    <span className="nf-brand-name">
      NutriFlow AI
      <small>Casa à Mesa <span className="nf-brand-version" aria-label={`Versão ${APP_VERSION}`}>v{APP_VERSION}</span></small>
    </span>
  </span>;
}
