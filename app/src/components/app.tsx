import { Header } from "./header";
import Content from "./content/index";
import { registerCustomElement } from "ojs/ojvcomponent";
import { createContext } from "preact";
import { useEffect, useState } from "preact/hooks";
import { debugLog } from "../libs/debug";

type Props = {
  appName: string;
};
const tempArray = new Uint32Array(10);
const convoUUID = window.crypto.getRandomValues(tempArray);

export const ConvoCtx = createContext("");

export const App = registerCustomElement("app-root", (props: Props) => {
  props.appName = "Generative AI JET UI";
  const [settingsOpened, setSettingsOpened] = useState<boolean>(false);

  const toggleDrawer = () => {
    setSettingsOpened(!settingsOpened);
  };

  // DB connectivity ping + keepalive (quiet success; info on first success/recovery; warn on failure)
  useEffect(() => {
    let cancelled = false;
    let wasUp = false;

    const ping = async () => {
      try {
        const res = await fetch("/api/kb/diag?tenantId=default", { cache: "no-store" as any });
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const json = await res.json();
        if (cancelled) return;
        if (json?.dbOk) {
          if (!wasUp) {
            console.info("DB: database active");
          }
          wasUp = true;
        } else {
          if (wasUp) {
            console.info("DB: connectivity lost");
          }
          wasUp = false;
          console.warn("DB: database not available");
          debugLog("DB diag payload:", json);
        }
      } catch (e) {
        if (!cancelled) {
          wasUp = false;
          console.warn("DB: database ping failed", e);
        }
      }
    };

    // initial ping
    ping();

    // keep alive every 60s
    const id = window.setInterval(() => ping(), 60000);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return (
    <div id="appContainer" class="oj-web-applayout-page">
      <ConvoCtx.Provider value={convoUUID[0].toString()}>
        {debugLog("UUID:", convoUUID[0].toString())}
        <Header appName={props.appName} onToggleDrawer={toggleDrawer} />
        <Content settingsOpened={settingsOpened} setSettingsOpened={setSettingsOpened} />
      </ConvoCtx.Provider>
    </div>
  );
});
