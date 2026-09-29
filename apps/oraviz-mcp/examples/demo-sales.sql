-- Demo data for OraViz MCP. Run as the app user (e.g. ORAVIZ) after creating it:
--   CREATE USER oraviz IDENTIFIED BY "OraViz2026" DEFAULT TABLESPACE USERS QUOTA UNLIMITED ON USERS;
--   GRANT CONNECT, RESOURCE TO oraviz;

DROP TABLE sales_demo PURGE;
CREATE TABLE sales_demo (
    sale_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region       VARCHAR2(20)  NOT NULL,
    channel      VARCHAR2(20)  NOT NULL,
    sale_month   DATE          NOT NULL,
    revenue      NUMBER(12,2)  NOT NULL,
    units        NUMBER(10)    NOT NULL,
    satisfaction NUMBER(3,1)   NOT NULL
);

INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2025-10-01', 27300.0, 606, 3.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2025-10-01', 17782.0, 306, 4.1);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2025-10-01', 23474.0, 460, 4.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2025-10-01', 15321.0, 239, 4.0);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2025-10-01', 31348.0, 549, 4.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2025-10-01', 20465.0, 409, 3.9);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2025-10-01', 19722.0, 313, 4.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2025-10-01', 12934.0, 230, 3.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2025-11-01', 30851.0, 629, 4.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2025-11-01', 20193.75, 325, 3.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2025-11-01', 26560.0, 482, 4.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2025-11-01', 17430.5, 363, 3.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2025-11-01', 35364.0, 579, 4.3);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2025-11-01', 23179.0, 429, 3.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2025-11-01', 21843.0, 464, 4.2);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2025-11-01', 14241.25, 237, 3.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2025-12-01', 33198.63, 626, 4.1);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2025-12-01', 21648.31, 470, 4.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2025-12-01', 28543.11, 483, 4.0);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2025-12-01', 18648.12, 358, 4.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2025-12-01', 38076.15, 846, 3.9);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2025-12-01', 24870.5, 428, 4.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2025-12-01', 23961.6, 469, 3.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2025-12-01', 15721.94, 245, 4.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-01-01', 27268.0, 478, 3.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-01-01', 17897.0, 357, 4.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-01-01', 23502.0, 373, 3.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-01-01', 15475.0, 276, 4.3);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-01-01', 30756.0, 627, 3.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-01-01', 20041.0, 323, 4.2);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-01-01', 19310.0, 351, 3.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-01-01', 12627.0, 263, 4.1);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-02-01', 26990.63, 442, 4.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-02-01', 17645.31, 326, 4.0);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-02-01', 23235.11, 494, 4.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-02-01', 15230.12, 253, 3.9);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-02-01', 30968.15, 584, 4.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-02-01', 20282.5, 440, 3.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-02-01', 19553.6, 331, 4.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-02-01', 12888.94, 247, 3.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-03-01', 25995.0, 577, 4.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-03-01', 16601.75, 286, 3.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-03-01', 21924.0, 429, 4.3);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-03-01', 14306.5, 223, 3.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-03-01', 29288.0, 513, 4.2);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-03-01', 19119.0, 382, 3.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-03-01', 18427.0, 292, 4.1);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-03-01', 12085.25, 215, 4.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-04-01', 23796.0, 485, 4.0);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-04-01', 15601.0, 251, 4.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-04-01', 20510.0, 372, 3.9);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-04-01', 13491.0, 281, 4.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-04-01', 27304.0, 447, 3.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-04-01', 17933.0, 332, 4.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-04-01', 17298.0, 368, 3.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-04-01', 10955.0, 182, 4.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-05-01', 21597.0, 407, 3.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-05-01', 14100.25, 306, 4.3);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-05-01', 18596.0, 315, 3.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-05-01', 12175.5, 234, 4.2);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-05-01', 24820.0, 551, 3.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-05-01', 16247.0, 280, 4.1);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-05-01', 15669.0, 307, 4.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-05-01', 10324.75, 161, 4.0);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-06-01', 20601.37, 361, 4.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-06-01', 13556.69, 271, 3.9);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-06-01', 17784.89, 282, 4.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-06-01', 11751.88, 209, 3.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-06-01', 23139.85, 472, 4.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-06-01', 15083.5, 243, 3.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-06-01', 14542.4, 264, 4.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-06-01', 9521.06, 198, 3.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-07-01', 20324.0, 333, 4.3);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-07-01', 13305.0, 246, 3.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-07-01', 17518.0, 372, 4.2);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-07-01', 11507.0, 191, 3.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-07-01', 23352.0, 440, 4.1);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-07-01', 15325.0, 333, 4.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-07-01', 14786.0, 250, 4.0);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-07-01', 9783.0, 188, 4.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-08-01', 21953.37, 487, 3.9);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-08-01', 14467.69, 249, 4.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-08-01', 18456.89, 361, 3.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-08-01', 12045.88, 188, 4.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-08-01', 24671.85, 432, 3.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-08-01', 16111.5, 322, 4.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-08-01', 15534.4, 246, 3.6);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-08-01', 10198.06, 182, 4.3);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Online', DATE '2026-09-01', 24301.0, 495, 3.5);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('North', 'Retail', DATE '2026-09-01', 15922.25, 256, 4.2);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Online', DATE '2026-09-01', 20940.0, 380, 3.4);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('South', 'Retail', DATE '2026-09-01', 13763.5, 286, 4.1);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Online', DATE '2026-09-01', 27884.0, 457, 4.8);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('East', 'Retail', DATE '2026-09-01', 18303.0, 338, 4.0);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Online', DATE '2026-09-01', 17653.0, 375, 4.7);
INSERT INTO sales_demo (region, channel, sale_month, revenue, units, satisfaction) VALUES ('West', 'Retail', DATE '2026-09-01', 11178.75, 186, 3.9);

-- A 26ai-style VECTOR table, so vector columns can be inspected and charted too.
DROP TABLE product_vectors PURGE;
CREATE TABLE product_vectors (
    product_name VARCHAR2(60),
    category     VARCHAR2(40),
    embedding    VECTOR(8, FLOAT32)
);

INSERT INTO product_vectors (product_name, category, embedding) VALUES ('Trail Runner GTX', 'Footwear', TO_VECTOR('[0.91, 0.12, 0.05, 0.33, 0.08, 0.02, 0.14, 0.27]'));
INSERT INTO product_vectors (product_name, category, embedding) VALUES ('City Runner', 'Footwear', TO_VECTOR('[0.88, 0.15, 0.07, 0.29, 0.11, 0.04, 0.10, 0.31]'));
INSERT INTO product_vectors (product_name, category, embedding) VALUES ('Alpine Shell', 'Outerwear', TO_VECTOR('[0.12, 0.83, 0.21, 0.07, 0.44, 0.09, 0.02, 0.18]'));
INSERT INTO product_vectors (product_name, category, embedding) VALUES ('Storm Parka', 'Outerwear', TO_VECTOR('[0.09, 0.79, 0.25, 0.05, 0.48, 0.12, 0.03, 0.15]'));
INSERT INTO product_vectors (product_name, category, embedding) VALUES ('Compact Tent', 'Camping', TO_VECTOR('[0.22, 0.31, 0.88, 0.19, 0.06, 0.71, 0.05, 0.09]'));
INSERT INTO product_vectors (product_name, category, embedding) VALUES ('Sleeping Bag -5C', 'Camping', TO_VECTOR('[0.18, 0.28, 0.81, 0.24, 0.10, 0.66, 0.07, 0.12]'));

COMMIT;
