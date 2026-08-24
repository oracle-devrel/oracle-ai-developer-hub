package com.example.creditdemo.helidon;

import org.slf4j.bridge.SLF4JBridgeHandler;

public final class Main {
    private Main() {
    }

    public static void main(String[] args) {
        SLF4JBridgeHandler.removeHandlersForRootLogger();
        SLF4JBridgeHandler.install();
        io.helidon.microprofile.cdi.Main.main(args);
    }
}
