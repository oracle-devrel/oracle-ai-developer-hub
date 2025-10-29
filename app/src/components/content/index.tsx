import { Chat } from "./chat";
import { Summary } from "./summary";
import { Settings } from "./settings";
import { Upload } from "./upload";
import "preact";
import "ojs/ojinputsearch";
import "oj-c/message-toast";
import "oj-c/drawer-popup";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import { MessageToastItem } from "oj-c/message-toast";
import { InputSearchElement } from "ojs/ojinputsearch";
import { useState, useEffect, useRef, useContext } from "preact/hooks";

import { initWebSocket } from "./websocket-interface";
import { InitStomp, sendPrompt } from "./stomp-interface";
import { Client } from "@stomp/stompjs";
import { ConvoCtx } from "../app";

type ServiceTypes = "text" | "summary" | "upload";
type BackendTypes = "java" | "python";
type Chat = {
  id?: number;
  question?: string;
  answer?: string;
  loading?: string;
};
type Model = {
  id: string;
  name: string;
  vendor: string;
  version: string;
  capabilities: Array<string>;
  timeCreated: string;
};

const defaultServiceType: string = localStorage.getItem("service") || "text";
type ContentProps = {
  settingsOpened: boolean;
  setSettingsOpened: (opened: boolean) => void;
};

const Content = ({ settingsOpened, setSettingsOpened }: ContentProps) => {
  const conversationId = useContext(ConvoCtx);
  const [update, setUpdate] = useState<Array<object>>([]);
  const [busy, setBusy] = useState<boolean>(false);
  const [summaryResults, setSummaryResults] = useState<string>("");
  const [modelId, setModelId] = useState<string | null>(null);
  const [summaryPrompt, setSummaryPrompt] = useState<string>();
  const [serviceType, setServiceType] = useState<ServiceTypes>(
    defaultServiceType as ServiceTypes
  );
  const backendType: BackendTypes = "java";
  const [ragEnabled, setRagEnabled] = useState<boolean>(false);
  const [question, setQuestion] = useState<string>("");
  const chatData = useRef<Array<object>>([]);
  const socket = useRef<WebSocket>();
  const finetune = useRef<boolean>(false);
  const [client, setClient] = useState<Client | null>(null);

  const messagesDP = useRef(
    new MutableArrayDataProvider<MessageToastItem["summary"], MessageToastItem>(
      [],
      { keyAttributes: "summary" }
    )
  );



  useEffect(() => {
    switch (serviceType) {
      case "text":
        setClient(
          InitStomp(setBusy, setUpdate, messagesDP, chatData, serviceType)
        );
        console.log("Running Generative service");
        return;
      case "summary":
        setClient(
          InitStomp(setBusy, setUpdate, messagesDP, chatData, serviceType)
        );
        console.log("Running Summarization service");
        return;
    }
    return () => {
      socket.current ? (socket.current.onclose = () => {}) : null;
      socket.current?.close();
      client?.deactivate();
    };
  }, [serviceType]);

  const handleQuestionChange = (
    event: InputSearchElement.ojValueAction<null, null>
  ) => {
    // if we are waiting for an answer to be returned, throw an alert and return
    if (busy) {
      messagesDP.current.data = [
        {
          summary: "Still waiting for an answer!",
          detail: "Hang in there a little longer.",
          autoTimeout: "on",
        },
      ];
      return;
    }
    if (event.detail.value) {
      setQuestion(event.detail.value);
      let tempArray = [...chatData.current];
      tempArray.push({
        id: tempArray.length as number,
        question: question,
      });
      chatData.current = tempArray;
      setUpdate(chatData.current);

      // adding loading animation while we wait for answer to come back
      let tempAnswerArray = [...chatData.current];
      tempAnswerArray.push({
        id: tempAnswerArray.length as number,
        loading: "loading",
      });
      chatData.current = tempAnswerArray;
      setUpdate(chatData.current);
      setBusy(true);

      if (ragEnabled) {
        // Use RAG endpoint for Java backend when RAG is enabled
        fetch("/api/genai/rag", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: question,
            tenantId: "default"
          }),
        })
          .then((response) => response.text())
          .then((answer) => {
            let tempArray = [...chatData.current];
            // Remove loading indicator
            tempArray.pop();
            // Add the answer
            tempArray.push({
              id: tempArray.length as number,
              answer: answer,
            });
            chatData.current = tempArray;
            setUpdate(chatData.current);
            setBusy(false);
          })
          .catch((error) => {
            console.error("RAG request failed:", error);
            let tempArray = [...chatData.current];
            tempArray.pop(); // Remove loading
            tempArray.push({
              id: tempArray.length as number,
              answer: "Sorry, I encountered an error while processing your question with RAG.",
            });
            chatData.current = tempArray;
            setUpdate(chatData.current);
            setBusy(false);
          });
      } else {
        sendPrompt(
          client,
          question,
          modelId!,
          conversationId!,
          finetune.current
        );
      }

      // Clear the input field after question is published
      setQuestion("");
    }
  };

  const handleFileUpload = (file: ArrayBuffer | Uint8Array) => {
    socket.current?.send(file);
  };

  const handleDrawerState = () => {
    setSettingsOpened(false);
  };
  const toggleDrawer = () => {
    setSettingsOpened(!settingsOpened);
  };
  const handleToastClose = () => {
    messagesDP.current.data = [];
  };

  const serviceTypeChangeHandler = (service: ServiceTypes) => {
    localStorage.setItem("service", service);
    setUpdate([]);
    chatData.current = [];
    setServiceType(service);
  };

  const modelIdChangeHandler = (value: string, modelType: boolean) => {
    if (value != null) setModelId(value);
    finetune.current = modelType;
  };
  const clearSummary = () => {
    setSummaryResults("");
  };

  const updateSummaryPrompt = (val: string) => {
    setSummaryPrompt(val);
  };
  const updateSummaryResults = (summary: string) => {
    setSummaryResults(summary);
  };

  return (
    <div class="oj-web-applayout-max-width oj-web-applayout-content oj-flex oj-sm-flex-direction-column demo-bg-main">
      <oj-c-drawer-popup
        edge="end"
        opened={settingsOpened}
        onojBeforeClose={handleDrawerState}
        aria-label="Settings Drawer"
      >
        <Settings
          aiServiceType={serviceType}
          backendType={backendType}
          ragEnabled={ragEnabled}
          aiServiceChange={serviceTypeChangeHandler}
          ragToggle={setRagEnabled}
          modelIdChange={modelIdChangeHandler}
        />
      </oj-c-drawer-popup>
      <div class="oj-flex-bar oj-flex-item demo-header oj-sm-12">
        <oj-c-message-toast
          data={messagesDP.current}
          position="top"
          onojClose={handleToastClose}
        ></oj-c-message-toast>
      </div>
      {serviceType === "text" && (
        <Chat
          data={update}
          question={question}
          questionChanged={handleQuestionChange}
          settingsOpened={settingsOpened}
        />
      )}

      {serviceType === "summary" && (
        <Summary
          fileChanged={handleFileUpload}
          summaryChanged={updateSummaryResults}
          summary={summaryResults}
          clear={clearSummary}
          prompt={updateSummaryPrompt}
          backendType={backendType}
          modelId={modelId}
        />
      )}
      {serviceType === "upload" && (
        <Upload backendType={backendType} modelId={modelId} />
      )}
    </div>
  );
};
export default Content;
