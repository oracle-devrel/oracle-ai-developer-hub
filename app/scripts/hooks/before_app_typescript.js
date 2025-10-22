/**
  Copyright (c) 2015, 2023, Oracle and/or its affiliates.
  Licensed under The Universal Permissive License (UPL), Version 1.0
  as shown at https://oss.oracle.com/licenses/upl/

*/
'use strict';
const fs = require('fs-extra');
const path = require('path');

module.exports = function (configObj) {
  return new Promise(async (resolve) => {
    try {
      console.log("Running before_app_typescript hook: staging src/libs -> web/libs");
      const srcDir = path.resolve('src', 'libs');
      const dstDir = path.resolve('web', 'libs');
      const exists = await fs.pathExists(srcDir);
      if (exists) {
        await fs.ensureDir(dstDir);
        await fs.copy(srcDir, dstDir, { overwrite: true, errorOnExist: false });
        console.log(`Copied ${srcDir} -> ${dstDir}`);
      } else {
        console.log(`Skipped copy: ${srcDir} does not exist`);
      }
    } catch (e) {
      console.warn(`before_app_typescript: libs copy skipped due to error: ${e && e.message ? e.message : e}`);
    }
    resolve(configObj);
  });
};
