"use client"

import { Header } from "@/components/layout/header"
import { ChatContainer } from "@/components/chat/chat-container"
import { CommandPalette } from "@/components/layout/command-palette"
import { FABMenu } from "@/components/layout/fab-menu"
import { SettingsDrawer } from "@/components/layout/settings-drawer"
import { DevToolsDrawer } from "@/components/layout/dev-tools-drawer"

export default function Home() {
  return (
    <div className="flex h-screen flex-col bg-background">
      <Header />
      <main className="flex-1 overflow-hidden">
        <ChatContainer />
      </main>
      <CommandPalette />
      <FABMenu />
      <SettingsDrawer />
      <DevToolsDrawer />
    </div>
  )
}
