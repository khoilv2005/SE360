# ================================================
# Network Security Groups (NSGs)
# Zero Trust Network Architecture
# ================================================

# ==================================================
# NSG for AKS Subnet (172.16.1.0/24)
# ==================================================
resource "azurerm_network_security_group" "aks_nsg" {
  name                = "nsg-aks-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    Environment = "Production"
    Purpose     = "AKS-Zero-Trust"
  }
}

# Inbound Rules for AKS
resource "azurerm_network_security_rule" "aks_allow_https_inbound" {
  name                        = "AllowHTTPSInbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["80", "443"]
  source_address_prefix       = "Internet"
  destination_address_prefix  = "172.16.1.0/24"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.aks_nsg.name
}

resource "azurerm_network_security_rule" "aks_allow_lb_inbound" {
  name                        = "AllowAzureLoadBalancerInbound"
  priority                    = 105
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "AzureLoadBalancer"
  destination_address_prefix  = "172.16.1.0/24"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.aks_nsg.name
  description                 = "Allow Azure Load Balancer health probes"
}

resource "azurerm_network_security_rule" "aks_deny_all_inbound" {
  name                        = "DenyAllInbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.aks_nsg.name
}

# Outbound Rules for AKS
resource "azurerm_network_security_rule" "aks_allow_db_outbound" {
  name                        = "AllowDatabaseOutbound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["5432", "6379", "10255", "443"]
  source_address_prefix       = "172.16.1.0/24"
  destination_address_prefix  = "172.16.2.0/24"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.aks_nsg.name
}

resource "azurerm_network_security_rule" "aks_allow_internet_outbound" {
  name                        = "AllowInternetOutbound"
  priority                    = 110
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = "172.16.1.0/24"
  destination_address_prefix  = "Internet"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.aks_nsg.name
  description                 = "Allow HTTPS to external APIs (VNPay, Mapbox)"
}

resource "azurerm_network_security_rule" "aks_allow_azure_services" {
  name                        = "AllowAzureServicesOutbound"
  priority                    = 120
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "172.16.1.0/24"
  destination_address_prefix  = "AzureCloud"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.aks_nsg.name
  description                 = "Allow access to Azure services (ACR, Monitor)"
}

# Associate NSG with AKS subnet
resource "azurerm_subnet_network_security_group_association" "aks_nsg_assoc" {
  subnet_id                 = azurerm_subnet.aks_subnet.id
  network_security_group_id = azurerm_network_security_group.aks_nsg.id
}

# ==================================================
# NSG for PostgreSQL Subnet (172.16.2.0/24)
# ==================================================
resource "azurerm_network_security_group" "postgres_nsg" {
  name                = "nsg-postgres-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    Environment = "Production"
    Purpose     = "Database-Security"
  }
}

# Inbound: Only from AKS subnet
resource "azurerm_network_security_rule" "postgres_allow_aks_inbound" {
  name                        = "AllowAKSInbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "5432"
  source_address_prefix       = "172.16.1.0/24"
  destination_address_prefix  = "172.16.2.0/24"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.postgres_nsg.name
}

resource "azurerm_network_security_rule" "postgres_deny_all_inbound" {
  name                        = "DenyAllInbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.postgres_nsg.name
}

# Outbound: Deny all (databases should not initiate connections)
resource "azurerm_network_security_rule" "postgres_deny_all_outbound" {
  name                        = "DenyAllOutbound"
  priority                    = 4096
  direction                   = "Outbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.postgres_nsg.name
}

# Associate NSG with PostgreSQL subnet
resource "azurerm_subnet_network_security_group_association" "postgres_nsg_assoc" {
  subnet_id                 = azurerm_subnet.postgres_subnet.id
  network_security_group_id = azurerm_network_security_group.postgres_nsg.id
}

# ==================================================
# NSG for Management Subnet (172.16.5.0/24)
# Optional - for future Bastion/Jump box
# ==================================================
resource "azurerm_network_security_group" "management_nsg" {
  name                = "nsg-management-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    Environment = "Production"
    Purpose     = "Management-Access"
  }
}

# Allow SSH from specific IPs only (customize this)
resource "azurerm_network_security_rule" "mgmt_allow_ssh" {
  name                        = "AllowSSHInbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = "*" # TODO: Replace with your IP
  destination_address_prefix  = "172.16.5.0/24"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.management_nsg.name
  description                 = "Allow SSH from admin IPs only"
}

resource "azurerm_network_security_rule" "mgmt_deny_all_inbound" {
  name                        = "DenyAllInbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.management_nsg.name
}
