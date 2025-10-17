package dev.victormartin.oci.genai.backend.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.oracle.bmc.generativeai.GenerativeAiClient;
import com.oracle.bmc.generativeai.model.ModelSummary;
import com.oracle.bmc.generativeai.requests.ListModelsRequest;
import com.oracle.bmc.generativeai.responses.ListModelsResponse;
import dev.victormartin.oci.genai.backend.backend.model.ModelInfo;
import dev.victormartin.oci.genai.backend.backend.model.ModelOption;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.*;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * Loads a static model catalog (classpath:model_catalog.json), overlays it with live OCI models, and
 * produces a filtered list of ModelOption for the current region/mode/gates.
 */
@Service
public class ModelCatalogService {

    private static final Logger log = LoggerFactory.getLogger(ModelCatalogService.class);

    private final ObjectMapper mapper = new ObjectMapper();
    private final Environment env;
    private final GenAiClientService mgmtClientService;

    public ModelCatalogService(Environment env, GenAiClientService mgmtClientService) {
        this.env = env;
        this.mgmtClientService = mgmtClientService;
    }

    public List<ModelOption> listModels(String task) {
        List<ModelInfo> catalog = loadCatalog();
        String regionEndpoint = normalizeRegion(env.getProperty("genai.region", "US_CHICAGO_1"));
        Set<String> enabledProviders = csvToSet(env.getProperty("genai.catalog.enabledProviders", ""));
        Set<String> blockedModels = csvToSet(env.getProperty("genai.catalog.blockedModels", ""));
        Set<String> preferredModels = csvToSet(env.getProperty("genai.catalog.preferredModels", ""));
        boolean geminiApproved = Boolean.parseBoolean(env.getProperty("genai.catalog.gates.geminiApproved", "false"));
        boolean externalHostingOk = Boolean.parseBoolean(env.getProperty("genai.catalog.gates.externalHostingOk", "true"));
        String servingMode = env.getProperty("genai.serving.chat.mode", "ON_DEMAND"); // ON_DEMAND | DEDICATED

        // Live management models (On-Demand) to map displayName -> OCID + version
        Map<String, ModelSummary> liveByDisplayName = fetchLiveModels();

        Predicate<ModelInfo> regionFilter = mi -> mi.regions() == null || mi.regions().isEmpty() || mi.regions().contains(regionEndpoint);
        Predicate<ModelInfo> taskFilter = mi -> task == null || task.isBlank() || mi.tasks() != null && mi.tasks().contains(task);
        Predicate<ModelInfo> providerFilter = mi -> enabledProviders.isEmpty() || enabledProviders.contains(mi.provider());
        Predicate<ModelInfo> blockFilter = mi -> !blockedModels.contains(mi.id());
        Predicate<ModelInfo> gatesFilter = mi -> {
            List<String> notes = mi.notes() == null ? Collections.emptyList() : mi.notes();
            if (notes.contains("approval_required") && !geminiApproved) return false;
            if (notes.contains("external_hosting") && !externalHostingOk) return false;
            return true;
        };
        Predicate<ModelInfo> modeFilter = mi -> {
            List<String> modes = mi.modes() == null ? List.of("ON_DEMAND") : mi.modes();
            return modes.contains(servingMode);
        };

        List<ModelInfo> filtered = catalog.stream()
                .filter(regionFilter.and(taskFilter).and(providerFilter).and(blockFilter).and(gatesFilter).and(modeFilter))
                .collect(Collectors.toList());

        // Rank preferred first
        Comparator<ModelInfo> ranking = Comparator
                .comparing((ModelInfo mi) -> preferredModels.contains(mi.id()) ? 0 : 1)
                .thenComparing((ModelInfo mi) -> Optional.ofNullable(mi.contextTokens()).orElse(0), Comparator.reverseOrder())
                .thenComparing(ModelInfo::id);

        filtered.sort(ranking);

        // Build ModelOption; for On-Demand, attempt to resolve ocid from live list by displayName == id
        List<ModelOption> out = new ArrayList<>();
        for (ModelInfo mi : filtered) {
            ModelSummary live = liveByDisplayName.get(mi.id());
            String ocid = live != null ? live.getId() : null;
            String version = live != null ? live.getVersion() : null;
            out.add(new ModelOption(
                    ocid,
                    mi.id(),
                    mi.provider(),
                    version,
                    mi.tasks(),
                    mi.modes(),
                    mi.contextTokens(),
                    mi.maxOutputTokens(),
                    mi.notes()
            ));
        }
        return out;
    }

    public List<ModelOption> listAll() {
        return listModels(null);
    }

    private List<ModelInfo> loadCatalog() {
        try (InputStream is = Thread.currentThread().getContextClassLoader().getResourceAsStream("model_catalog.json")) {
            if (is == null) {
                log.warn("model_catalog.json not found on classpath; returning empty catalog");
                return List.of();
            }
            return mapper.readValue(is, new TypeReference<List<ModelInfo>>() {});
        } catch (Exception e) {
            log.error("Failed to load/parse model_catalog.json: {}", e.getMessage());
            return List.of();
        }
    }

    private Map<String, ModelSummary> fetchLiveModels() {
        try {
            String compartmentId = env.getProperty("genai.compartment_id");
            if (compartmentId == null || compartmentId.isBlank()) {
                log.warn("genai.compartment_id not configured; skipping live model overlay");
                return Map.of();
            }
            GenerativeAiClient client = mgmtClientService.getClient();
            ListModelsResponse response = client.listModels(ListModelsRequest.builder().compartmentId(compartmentId).build());
            return response.getModelCollection().getItems()
                    .stream()
                    .collect(Collectors.toMap(ModelSummary::getDisplayName, m -> m, (a, b) -> a));
        } catch (Exception e) {
            log.warn("Live model overlay failed: {}", e.getMessage());
            return Map.of();
        }
    }

    private static Set<String> csvToSet(String csv) {
        if (csv == null || csv.isBlank()) return Collections.emptySet();
        return Arrays.stream(csv.split(","))
                .map(String::trim)
                .filter(s -> !s.isBlank())
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    // Convert Spring genai.region value like "US_CHICAGO_1" to endpoint token "us-chicago-1"
    private static String normalizeRegion(String regionCode) {
        if (regionCode == null) return "us-chicago-1";
        return regionCode.toLowerCase(Locale.ROOT).replace('_', '-');
    }
}
