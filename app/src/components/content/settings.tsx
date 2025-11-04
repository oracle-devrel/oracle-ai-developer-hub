import { useEffect, useRef, useState, useContext } from "preact/hooks";
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
import { getKv, setKv } from "../../libs/memory";
import { ConvoCtx } from "../app";

type ServiceTypeVal = "text" | "summary" | "upload";
type Services = {
  label: string;
  value: ServiceTypeVal;
};
type Props = {
  aiServiceType: ServiceTypeVal;
  ragEnabled: boolean;
  theme: string;
  aiServiceChange: (service: ServiceTypeVal) => void;
  ragToggle: (enabled: boolean) => void;
  themeChange: (theme: string) => void;
  modelIdChange: (modelId: any, modelData: any) => void;
  onLanguageChange?: (language: string) => void;
};

const serviceTypes = [
  { value: "text", label: "Generative Text" },
  { value: "summary", label: "Summarize" },
  { value: "upload", label: "RAG Knowledge Base" },
];

const languages = [
  { value: "english", label: "English" },
  { value: "polish", label: "Polish" },
  { value: "spanish", label: "Spanish" },
  { value: "french", label: "French" },
  { value: "german", label: "German" },
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

const languageOptionsDP = new MutableArrayDataProvider<
  string,
  { label: string; value: string }
>(languages, { keyAttributes: "value" });

export const Settings = (props: Props) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleServiceTypeChange = (event: any) => {
    if (event.detail.updatedFrom === "internal")
      props.aiServiceChange(event.detail.value);
  };

  const modelDP = useRef(
    new MutableArrayDataProvider<string, {}>([], {
      keyAttributes: "id",
    })
  );
  const endpoints = useRef<Array<Endpoint>>();
  const conversationId = useContext(ConvoCtx);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("english");
  const [prefsLoaded, setPrefsLoaded] = useState<boolean>(false);
  const [modelsLoaded, setModelsLoaded] = useState<boolean>(false);

  const fetchModels = async (retries = 3) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const primaryUrl = "/api/genai/models";

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
        setModelsLoaded(true);
        return; // Success, exit function
        } catch (error: any) {
          console.error(`Model fetch attempt ${attempt} failed: `, error.message);
        if (attempt === retries) {
          // All retries failed
          modelDP.current.data = []; // Clear models on error
          setErrorMessage("Failed to fetch models after retries. Please check your backend connection.");
          setModelsLoaded(true);
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
    (async () => {
      await fetchEndpoints();
      await fetchModels();
      try {
        await loadPrefs(conversationId);
      } catch (e) {
        console.warn("loadPrefs failed", e);
      }
    })();
  }, []);


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
    setSelectedModelId(selected as string);
    try {
      await setKv(conversationId, "userPrefs", { modelId: selected, language: selectedLanguage }, 3600);
    } catch (e) {
      console.warn("savePrefs failed", e);
    }
  };


  const languageChangeHandler = async (event: any) => {
    if (event.detail.updatedFrom === "internal") {
      const lang = event.detail.value;
      setSelectedLanguage(lang);
      props.onLanguageChange?.(lang);
      try {
        await setKv(conversationId, "userPrefs", { modelId: selectedModelId, language: lang }, 3600);
      } catch (e) {
        console.warn("savePrefs failed", e);
      }
    }
  };

  // KV-backed prefs
  async function loadPrefs(conversationId: string) {
    const prefs = (await getKv(conversationId, "userPrefs")) || { modelId: null, language: "english" };
    try {
      if (prefs.modelId) {
        setSelectedModelId(prefs.modelId as string);
      }
      if (prefs.language) {
        setSelectedLanguage(prefs.language as string);
      }
    } finally {
      setPrefsLoaded(true);
    }
  }

  async function savePrefs(conversationId: string) {
    try {
      const prefs = { modelId: selectedModelId, language: selectedLanguage };
      await setKv(conversationId, "userPrefs", prefs, 3600);
    } catch (e) {
      console.warn("savePrefs failed", e);
    }
  }

  // Auto-select default model on first load when KV has no model
  async function ensureDefaultModel() {
    try {
      if (selectedModelId) return; // nothing to do
      const asyncIterator = modelDP.current.fetchFirst()[Symbol.asyncIterator]();
      const result = await asyncIterator.next();
      const data = (result.value?.data as Array<Model>) || [];
      if (data.length === 0) return;

      let defaultId: string | null = null;
      try {
        const res = await fetch("/api/genai/default-model");
        if (res.ok) {
          const json = await res.json();
          if (json?.modelId) defaultId = json.modelId as string;
        }
      } catch {
        // ignore; will fallback
      }

      let chosen = (defaultId && data.find((m) => m.id === defaultId)) ? defaultId! : data[0].id;

      // Resolve finetune/endpoint mapping similar to modelChangeHandler
      let finetune = false;
      const idx = data.find((e: Model) => e.id === chosen);
      if (idx?.capabilities.includes("FINE_TUNE")) {
        finetune = true;
        const endpointId = endpoints.current?.find((e: Endpoint) => e.model === chosen)?.id;
        if (endpointId) chosen = endpointId;
      }

      setSelectedModelId(chosen);
      props.modelIdChange(chosen, finetune);
      await setKv(conversationId, "userPrefs", { modelId: chosen, language: selectedLanguage }, 3600);
    } catch (e) {
      console.warn("ensureDefaultModel failed", e);
    }
  }

  useEffect(() => {
    if (modelsLoaded && prefsLoaded && !selectedModelId) {
      ensureDefaultModel();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelsLoaded, prefsLoaded, selectedModelId]);

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
      </>
      <>
        <h2 class="oj-typography-heading-sm">Language Preference</h2>
        <oj-c-form-layout>
          <oj-c-select-single
            data={languageOptionsDP}
            labelHint="Preferred Language"
            itemText="label"
            value={selectedLanguage}
            onvalueChanged={languageChangeHandler}
          ></oj-c-select-single>
        </oj-c-form-layout>
      </>
    </div>
  );
};
