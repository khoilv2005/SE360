terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0"
    }
  }

  # --- ACTION: COMMENT TOÀN BỘ BLOCK NÀY (BAO GỒM CẢ DÒNG MỞ VÀ ĐÓNG) ---
  # backend "azurerm" {
  #   resource_group_name  = "rg-uitgo-tfstate"
  #   storage_account_name = "stuitgotfstate"
  #   container_name       = "tfstate"
  #   key                  = "prod.terraform.tfstate"
  # }
  # ----------------------------------------------------------------------
}

provider "azurerm" {
  features {}
  subscription_id = "d8ece151-084a-418c-a446-0ff133a2d388"
}