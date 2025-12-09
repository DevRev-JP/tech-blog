package sla

default priority = "Low"

priority = "High" if {
  input.customer_tier == "Platinum"
  input.issue == "Critical"
}

priority = "Medium" if {
  input.customer_tier == "Gold"
  input.issue == "Critical"
}

priority = "Medium" if {
  input.customer_tier == "Platinum"
  input.issue == "High"
}

