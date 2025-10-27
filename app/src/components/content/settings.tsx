import { useEffect, useRef, useState } from "preact/hooks";
import "oj-c/radioset";
import "oj-c/form-layout";
import "oj-c/select-single";
import "ojs/ojswitch";
import "ojs/ojlistitemlayout";
import "ojs/ojhighlighttext";
import "ojs/ojmessages";
import "oj-c/button";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import { ojSelectSingle } from "@oracle/oraclejet/ojselectsingle";

type ServiceTypeVal = "text" | "summary" | "sim" | "upload";
type BackendTypeVal = "java" | "python";
type Services = {
  label: string;
  value: ServiceTypeVal;
};
type Props = {
  aiServiceType: ServiceTypeVal;
  backendType: BackendTypeVal;
  ragEnabled: boolean;
  theme: string;
  aiServiceChange: (service: ServiceTypeVal) => void;
  backendChange: (backend: BackendTypeVal) => void;
  ragToggle: (enabled: boolean) => void;
  themeChange: (theme: string) => void;
  modelIdChange: (modelId: any, modelData: any) => void;
};

const serviceTypes = [
  { value: "text", label: "Generative Text" },
  { value: "summary", label: "Summarize" },
  { value: "upload", label: "Upload" },
];
// { value: "sim", label: "Simulation" },

const backendTypes = [
  { value: "java", label: "Java" },
  { value: "python", label: "Python" },
];
type Model = {
  id: string;
  name: string;
  vendor: string;
  version: string;
  capabilities: Array<string>;
  timeCreated: string;
};
type Endpoint = {
  id: string;
  name: string;
  state: string;
  model: string;
  timeCreated: string;
};
const serviceOptionsDP = new MutableArrayDataProvider<
  Services["value"],
  Services
>(serviceTypes, { keyAttributes: "value" });
const backendOptionsDP = new MutableArrayDataProvider<
  Services["value"],
  Services
>(backendTypes, { keyAttributes: "value" });

export const Settings = (props: Props) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleServiceTypeChange = (event: any) => {
    if (event.detail.updatedFrom === "internal")
      props.aiServiceChange(event.detail.value);
  };
  const handleBackendTypeChange = (event: any) => {
    if (event.detail.updatedFrom === "internal")
      props.backendChange(event.detail.value);
  };

  const modelDP = useRef(
    new MutableArrayDataProvider<string, {}>([], {
      keyAttributes: "id",
    })
  );
  const endpoints = useRef<Array<Endpoint>>();

  const fetchModels = async (retries = 3) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const isHttps = window.location.protocol === "https:";
        const pythonUrl = `${isHttps ? "https://" : "http://"}${window.location.hostname}:1987/models`;
        const primaryUrl =
          props.backendType === "python" && !isHttps ? pythonUrl : "/api/genai/models";

        let response: Response;
        try {
          response = await fetch(primaryUrl);
          if (!response.ok) throw new Error(`Response status: ${response.status}`);
        } catch (e) {
          // Fallback: if Python endpoint refused or blocked (mixed content), use Java endpoint
          if (primaryUrl !== "/api/genai/models") {
            response = await fetch("/api/genai/models");
            if (!response.ok) throw new Error(`Response status: ${response.status}`);
          } else {
            throw e;
          }
        }
        const json = await response.json();
        const result = json.filter((model: Model) => {
          if (
            model.capabilities.includes("CHAT") &&
            (model.vendor === "cohere" || model.vendor === "meta" || model.vendor === "xai")
          )
            return model;
        });
        modelDP.current.data = result;
        setErrorMessage(null);
        return; // Success, exit function
      } catch (error: any) {
        console.error(`Model fetch attempt ${attempt} failed (${props.backendType}): `, error.message);
        if (attempt === retries) {
          // All retries failed
          modelDP.current.data = []; // Clear models on error
          setErrorMessage("Failed to fetch models after retries. Please check your backend connection.");
        } else {
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s before retry
        }
      }
    }
  };
  const fetchEndpoints = async () => {
    try {
      const response = await fetch("/api/genai/endpoints");
      if (!response.ok) {
        throw new Error(`Response status: ${response.status}`);
      }
      const json = await response.json();
      const result = json.filter((endpoint: Endpoint) => {
        // add filtering code here
        return endpoint;
      });
      endpoints.current = result;
    } catch (error: any) {
      console.log(
        "Java service not available for fetching list of Endpoints: ",
        error.message
      );
    }
  };

  useEffect(() => {
    fetchEndpoints();
    fetchModels();
  }, []);

  // Re-fetch models when backend selection changes so Python uses OCI directly
  useEffect(() => {
    fetchModels();
  }, [props.backendType]);

  const modelChangeHandler = async (
    event: ojSelectSingle.valueChanged<string, {}>
  ) => {
    let selected = event.detail.value;
    let finetune = false;
    const asyncIterator = modelDP.current.fetchFirst()[Symbol.asyncIterator]();
    let result = await asyncIterator.next();
    let value = result.value;
    let data = value.data as Array<Model>;
    let idx = data.find((e: Model) => {
      if (e.id === selected) return e;
    });
    if (idx?.capabilities.includes("FINE_TUNE")) {
      finetune = true;
      let endpointId = endpoints.current?.find((e: Endpoint) => {
        if (e.model === event.detail.value) {
          return e.id;
        }
      });
      selected = endpointId ? endpointId.id : event.detail.value;
    }
    props.modelIdChange(selected, finetune);
  };

  const runDiag = async (_ev: any) => {
    try {
      const res = await fetch("/api/kb/diag?tenantId=default");
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const json = await res.json();
      console.log("KB DIAG:", json);
      setErrorMessage(null);
    } catch (e: any) {
      setErrorMessage(`KB diag failed: ${e?.message || e}`);
      console.error("KB DIAG failed:", e);
    }
  };

  const modelTemplate = (item: any) => {
    return (
      <oj-list-item-layout class="oj-listitemlayout-padding-off">
        <span class="oj-typography-body-md oj-text-color-primary">
          <oj-highlight-text
            text={item.item.data.name}
            match-text={item.searchText}
          ></oj-highlight-text>
        </span>
        <span
          slot="secondary"
          class="oj-typography-body-sm oj-text-color-secondary"
        >
          <oj-highlight-text
            text={JSON.stringify(item.item.data.capabilities)}
            match-text={item.searchText}
          ></oj-highlight-text>
        </span>
      </oj-list-item-layout>
    );
  };

  return (
    <div class="oj-sm-margin-4x">
      {errorMessage && (
        <oj-messages
          messages={[{ severity: "error", summary: errorMessage }]}
        ></oj-messages>
      )}
      <h2 class="oj-typography-heading-sm">AI service types</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="serviceTypeRadioset"
          value={props.aiServiceType}
          labelHint="AI service options"
          options={serviceOptionsDP}
          onvalueChanged={handleServiceTypeChange}
        ></oj-c-radioset>
      </oj-c-form-layout>
      <h2 class="oj-typography-heading-sm">Backend service types</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="backendTypeRadioset"
          value={props.backendType}
          labelHint="Backend options"
          options={backendOptionsDP}
          onvalueChanged={handleBackendTypeChange}
        ></oj-c-radioset>
      </oj-c-form-layout>
      <h2 class="oj-typography-heading-sm">Theme</h2>
      <oj-c-form-layout>
        <oj-c-radioset
          id="themeRadioset"
          value={props.theme}
          labelHint="Theme options"
          options={new MutableArrayDataProvider([{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }], { keyAttributes: "value" })}
          onvalueChanged={(event: any) => {
            if (event.detail.updatedFrom === "internal")
              props.themeChange(event.detail.value);
          }}
        ></oj-c-radioset>
      </oj-c-form-layout>
      {props.backendType === "java" && (
        <>
          <h2 class="oj-typography-heading-sm">RAG Options</h2>
          <oj-c-form-layout>
            <oj-switch
              id="ragSwitch"
              value={props.ragEnabled}
              labelHint="Enable Retrieval-Augmented Generation (RAG)"
              onvalueChanged={(event: any) => {
                if (event.detail.updatedFrom === "internal") {
                  props.ragToggle(event.detail.value);
                }
              }}
            ></oj-switch>
          </oj-c-form-layout>
          <oj-c-form-layout>
            <oj-c-button label="Check RAG status" onojAction={runDiag}></oj-c-button>
          </oj-c-form-layout>
        </>
      )}
      {props.aiServiceType == "text" && (props.backendType == "java" || props.backendType == "python") && (
        <>
          <h2 class="oj-typography-heading-sm">Model options</h2>
          <oj-c-form-layout>
            <oj-c-select-single
              data={modelDP.current}
              labelHint={"Model"}
              itemText={"name"}
              onvalueChanged={modelChangeHandler}
            >
              <template slot="itemTemplate" render={modelTemplate}></template>
            </oj-c-select-single>
          </oj-c-form-layout>
        </>
      )}
    </div>
  );
};
