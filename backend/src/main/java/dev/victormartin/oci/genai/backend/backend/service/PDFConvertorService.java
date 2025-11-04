package dev.victormartin.oci.genai.backend.backend.service;

import java.io.File;
import java.io.IOException;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.io.RandomAccessRead;
import org.apache.pdfbox.io.RandomAccessReadBufferedFile;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.ResourceUtils;

@Service
public class PDFConvertorService {
    Logger log = LoggerFactory.getLogger(PDFConvertorService.class);

    public String convert(String filePath) {
        try {
            File file = ResourceUtils.getFile(filePath);
            try (RandomAccessRead rar = new RandomAccessReadBufferedFile(file);
                 PDDocument doc = Loader.loadPDF(rar)) {
                return new PDFTextStripper().getText(doc);
            }
        } catch (IOException e) {
            log.error("PDF conversion failed: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
