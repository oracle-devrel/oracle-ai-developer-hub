# Copyright (c) 2025 Oracle and/or its affiliates.
#
# The Universal Permissive License (UPL), Version 1.0
#
# Subject to the condition set forth below, permission is hereby granted to any
# person obtaining a copy of this software, associated documentation and/or data
# (collectively the "Software"), free of charge and under any and all copyright
# rights in the Software, and any and all patent rights owned or freely
# licensable by each licensor hereunder covering either (i) the unmodified
# Software as contributed to or provided by such licensor, or (ii) the Larger
# Works (as defined below), to deal in both
#
# (a) the Software, and
# (b) any piece of software and/or hardware listed in the lrgrwrks.txt file if
# one is included with the Software (each a "Larger Work" to which the Software
# is contributed by such licensors),
# without restriction, including without limitation the rights to copy, create
# derivative works of, display, perform, and distribute the Software and make,
# use, sell, offer for sale, import, export, have made, and have sold the
# Software and the Larger Work(s), and to sublicense the foregoing rights on
# either these or other terms.
#
# This license is subject to the following condition:
# The above copyright notice and either this complete permission notice or at
# a minimum a reference to the UPL must be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

terraform {
  required_version = ">= 0.12.0"
}

provider "oci" {
  tenancy_ocid = var.tenancy_ocid
  region       = var.region
}

resource "oci_database_autonomous_database" "autonomous_ai_database" {  
  compartment_id = var.compartment_ocid
  admin_password = var.admin_password
  autonomous_maintenance_schedule_type = var.autonomous_maintenance_schedule_type
  compute_count = var.compute_count
  compute_model = var.compute_model
  data_storage_size_in_gb = var.data_storage_size_in_gb
  display_name   = var.display_name
  db_name = local.db_name_trimmed
  db_version = var.db_version
  db_workload = var.db_workload  
  is_dedicated = var.is_dedicated
  is_dev_tier = var.is_dev_tier
  is_mtls_connection_required = var.is_mtls_connection_required
  is_preview_version_with_service_terms_accepted = var.is_preview_version_with_service_terms_accepted
  license_model = var.license_model
}
 
resource "random_string" "db_suffix" {
  length  = 12
  special = false
  upper   = false
} 
locals {
  db_prefix = "DevDB"
  db_name   = "${local.db_prefix}${random_string.db_suffix.result}"
  db_name_trimmed = substr(local.db_name, 0, 11)  
}
locals { 
  timestamp        = "${formatdate("YYYY-MM-DD-hhmmss", timestamp())}" 
}
