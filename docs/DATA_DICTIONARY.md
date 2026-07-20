# Data Dictionary

## Dataset Overview
This repository contains delivery operations data used by the DeliveryPulse dashboard.
The core datasets cover customer transactions, delivery performance, route context, and SLA-related metrics.

Last Updated: 2026-07-20

Maintained By: Data Engineering Team

## Column to KPI Mapping

### Monthly Revenue
- **Formula**: SUM(transaction_amount)
- **Related Columns**: transaction_amount, transaction_date
- **Why It Matters**: Tracks total company revenue over time and supports finance reporting.
- **Update Frequency**: Daily

### Sales Velocity
- **Formula**: COUNT(transactions) / days
- **Related Columns**: transaction_date
- **Why It Matters**: Measures sales activity rate and momentum.
- **Update Frequency**: Weekly

### SLA Compliance
- **Formula**: 1 - (late deliveries / total deliveries)
- **Related Columns**: delivery_minutes, rider_delay_minutes
- **Why It Matters**: Core operational metric for the business.
- **Update Frequency**: Daily

### Delay Hotspots
- **Formula**: AVG(delivery_minutes) grouped by zone
- **Related Columns**: zone, delivery_minutes
- **Why It Matters**: Identifies locations where delays are concentrated.
- **Update Frequency**: Daily

### Rider Performance
- **Formula**: AVG(rider_delay_minutes)
- **Related Columns**: rider_delay_minutes, order_id
- **Why It Matters**: Helps management identify rider-related delay patterns.
- **Update Frequency**: Weekly

### Route Efficiency
- **Formula**: delivery_minutes / distance_km
- **Related Columns**: delivery_minutes, distance_km
- **Why It Matters**: Shows whether longer routes are causing disproportionate delays.
- **Update Frequency**: Weekly

## Ambiguous Columns & Resolutions

### Column: transaction_amount
- **Original Ambiguity**: Is this the order subtotal, total paid amount, or refund value?
- **Resolved Meaning**: Gross revenue paid by the customer for a completed transaction.
- **Business Interpretation**: Used for revenue analysis and average order value reporting.
- **Proposed Rename**: gross_transaction_amount
- **Risk If Misunderstood**: Revenue reporting could double count discounts or refunds.

### Column: zone
- **Original Ambiguity**: Is this a sales territory, delivery area, or customer region?
- **Resolved Meaning**: Operational service zone used by delivery teams.
- **Business Interpretation**: Supports SLA and route analysis by geography.
- **Proposed Rename**: delivery_zone
- **Risk If Misunderstood**: Teams may compare the wrong geographic dimension.

### Column: flag_churn
- **Original Ambiguity**: Does it mean currently churned or likely to churn later?
- **Resolved Meaning**: Historical churn indicator for whether a customer left within the retention window.
- **Business Interpretation**: Target variable for retention analysis and predictive modeling.
- **Proposed Rename**: has_churned_90d
- **Risk If Misunderstood**: Models can be trained on the wrong outcome definition.

## Column Relationships

### Revenue per Customer
- **Definition**: SUM(transaction_amount) grouped by customer_id
- **How It Matters**: Identifies high-value customers for retention and upsell opportunities.
- **Example**: Top customers drive a disproportionate share of revenue.
- **Related Columns**: customer_id, transaction_amount, transaction_date

### Delivery Delay by Zone
- **Definition**: AVG(delivery_minutes) grouped by zone
- **How It Matters**: Highlights operational bottlenecks and recurring SLA risk areas.
- **Example**: North zone may consistently exceed SLA thresholds during peak hours.
- **Related Columns**: zone, delivery_minutes, rider_delay_minutes

### Route Impact on SLA
- **Definition**: Compare delivery_minutes against distance_km
- **How It Matters**: Shows whether route length is a major driver of lateness.
- **Example**: Longer routes may explain part of the delay increase.
- **Related Columns**: delivery_minutes, distance_km, zone

## Columns

### customer_id
- **Type**: Integer
- **Business Meaning**: Unique customer identifier from CRM system
- **Example**: 12456
- **Null Handling**: Never null (primary key)
- **Related KPI**: Customer tracking, lifetime value calculation
- **Updates**: Assigned when customer is created in CRM

### customer_name
- **Type**: String
- **Business Meaning**: Full customer name used by support and operations teams
- **Example**: Alice Smith
- **Null Handling**: Should rarely be null
- **Related KPI**: Customer support lookup, retention analysis
- **Updates**: Sourced from CRM master data

### transaction_amount
- **Type**: Float
- **Business Meaning**: Revenue from a single transaction
- **Example**: 150.99
- **Unit**: USD
- **Null Handling**: Very rare - investigate if found
- **Related KPI**: Monthly revenue, average transaction value, customer lifetime value
- **Updates**: Set when transaction completes

### transaction_date
- **Type**: Datetime
- **Business Meaning**: Date the transaction was completed
- **Example**: 2025-01-15
- **Null Handling**: Never null
- **Related KPI**: Sales velocity, monthly revenue, trend analysis
- **Updates**: Captured at completion time

### delivery_minutes
- **Type**: Float
- **Business Meaning**: Total delivery duration in minutes
- **Example**: 42.5
- **Null Handling**: Investigate if missing
- **Related KPI**: SLA compliance, average delivery time
- **Updates**: Calculated after delivery completion

### distance_km
- **Type**: Float
- **Business Meaning**: Distance from restaurant to customer
- **Example**: 3.8
- **Null Handling**: Should not be null
- **Related KPI**: Route efficiency, delay analysis
- **Updates**: Recorded when order is assigned

### zone
- **Type**: String
- **Business Meaning**: Operational delivery zone
- **Example**: North
- **Null Handling**: Should be present for reporting
- **Related KPI**: Delay hotspots, SLA compliance by geography
- **Updates**: Maintained by operations team

### rider_delay_minutes
- **Type**: Float
- **Business Meaning**: Delay minutes attributable to rider handling
- **Example**: 6.0
- **Null Handling**: Can be null if delay attribution is unavailable
- **Related KPI**: Rider performance, delay root cause analysis
- **Updates**: Derived during operations review

### order_id
- **Type**: Integer
- **Business Meaning**: Unique identifier for each delivery order
- **Example**: 101
- **Null Handling**: Never null
- **Related KPI**: Order tracking, delivery performance reporting
- **Updates**: Created when the order enters the system

### delay_bucket
- **Type**: String
- **Business Meaning**: Derived delay severity band for reporting
- **Example**: medium
- **Null Handling**: Derived field, so should not be null
- **Related KPI**: Delay frequency, operational alerting
- **Updates**: Generated from delivery performance rules

### flag_churn
- **Type**: Integer
- **Business Meaning**: Churn indicator for whether a customer left within the retention window
- **Example**: 0
- **Null Handling**: Should never be null in a labeled training dataset
- **Related KPI**: Churn rate prediction, retention model training
- **Updates**: Set after the retention observation window closes