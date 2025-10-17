package dev.victormartin.oci.genai.backend.backend.controller;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import dev.victormartin.oci.genai.backend.backend.model.ModelOption;
import dev.victormartin.oci.genai.backend.backend.service.ModelCatalogService;

@Validated
@RestController
public class ModelsController {

    private static final Logger log = LoggerFactory.getLogger(ModelsController.class);

    private final ModelCatalogService catalog;

    public ModelsController(ModelCatalogService catalog) {
        this.catalog = catalog;
    }

    /**
     * Returns available models filtered for the current region/mode/gates, optionally by task.
     * task can be one of: chat, summarize, text, embed, rerank
     */
    @GetMapping(value = "/api/models", produces = MediaType.APPLICATION_JSON_VALUE)
    public List<ModelOption> list(@RequestParam(name = "task", required = false) String task) {
        log.info("GET /api/models task={}", task);
        return (task == null || task.isBlank())
                ? catalog.listAll()
                : catalog.listModels(task.toLowerCase());
    }
}
