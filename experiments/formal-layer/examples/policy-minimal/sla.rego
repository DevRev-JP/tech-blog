package sla

default priority = "Low"

priority = "High" if {
  input.customer_tier == "Platinum"
  input.issue == "Critical"
}

