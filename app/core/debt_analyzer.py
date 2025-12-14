import pandas as pd
from typing import Optional, Dict, List, Tuple
import math
import numpy as np


class DebtAnalyzer:
    def __init__(self):
        self.loans_df = pd.DataFrame()
        self.cards_df = pd.DataFrame()
        self.payments_df = pd.DataFrame()
        self.credit_score_df = pd.DataFrame()
        self.cashflow_df = pd.DataFrame()
        self.offers = []

    def load_data_from_streams(
        self,
        loans_stream,
        cards_stream,
        payments_stream,
        credit_stream,
        cashflow_stream,
        offers_data,
    ):
        """Load all data from StringIO streams and parsed JSON"""
        self.loans_df = pd.read_csv(loans_stream)
        self.cards_df = pd.read_csv(cards_stream)
        self.payments_df = pd.read_csv(payments_stream)
        self.credit_score_df = pd.read_csv(credit_stream)
        self.cashflow_df = pd.read_csv(cashflow_stream)
        self.offers = offers_data

    def get_product_data(self, customer_id: str, product_type: str) -> Optional[Dict]:
        """Retrieve product data for a specific customer and product type"""
        match product_type:
            case "loan":
                product = self.loans_df[self.loans_df["customer_id"] == customer_id]
                if product.empty:
                    return None
                row = product.iloc[0]
                return {
                    "product_id": row["loan_id"],
                    "product_type": "loan",
                    "sub_product_type": row["product_type"],
                    "balance": row["principal"],
                    "annual_rate_pct": row["annual_rate_pct"],
                    "remaining_term_months": row["remaining_term_months"],
                    "days_past_due": row["days_past_due"],
                    "monthly_payment": row["loan_monthly_payment"],
                    "late_fee_amount": row["late_fee_amount"],
                    "penalty_rate_pct": row["penalty_rate_pct"],
                    "collateral": row["collateral"],
                }
            case "card":
                product = self.cards_df[self.cards_df["customer_id"] == customer_id]
                if product.empty:
                    return None
                row = product.iloc[0]
                return {
                    "product_id": row["card_id"],
                    "product_type": "card",
                    "sub_product_type": row["product_type"],
                    "balance": row["balance"],
                    "annual_rate_pct": row["annual_rate_pct"],
                    "min_payment_pct": row["min_payment_pct"],
                    "days_past_due": row["days_past_due"],
                    "late_fee_amount": row["late_fee_amount"],
                    "penalty_rate_pct": row["penalty_rate_pct"],
                    "credit_limit": row["card_credit_limit"],
                }
            case _:
                return None

    def get_customer_data(self, customer_id: str) -> Optional[Dict]:
        """Get customer cashflow and credit score data"""
        cashflow_data = self.cashflow_df[self.cashflow_df["customer_id"] == customer_id]
        credit_data = self.credit_score_df[
            self.credit_score_df["customer_id"] == customer_id
        ]

        if cashflow_data.empty or credit_data.empty:
            return None

        cashflow = cashflow_data.iloc[0]
        credit = credit_data.iloc[0]

        return {
            "monthly_income": cashflow["monthly_income_avg"],
            "income_variability_pct": cashflow["income_variability_pct"],
            "essential_expenses": cashflow["essential_expenses_avg"],
            "credit_score": credit["credit_score"],
        }

    def calculate_monthly_rate(self, annual_rate_pct: float) -> float:
        """Convert annual rate to monthly rate"""
        return (annual_rate_pct / 100) / 12

    def calculate_minimum_payment_card(
        self, balance: float, min_payment_pct: float
    ) -> float:
        """Calculate minimum payment for credit card"""
        min_payment = balance * (min_payment_pct / 100)
        return max(min_payment, 25)  # Floor of $25

    def scenario_minimum_payment(self, product: Dict, customer: Dict) -> Dict:
        """Scenario 1: Minimum Payment Strategy"""
        balance = product["balance"]
        original_balance = balance

        # Determine interest rate (use penalty rate if past due)
        if product["days_past_due"] > 0:
            annual_rate = product["penalty_rate_pct"]
        else:
            annual_rate = product["annual_rate_pct"]

        monthly_rate = self.calculate_monthly_rate(annual_rate)

        monthly_projection = []
        month = 0
        total_paid = 0
        total_interest = 0

        while (
            balance > 0.01 and month < 600
        ):  # Cap at 50 years to prevent infinite loop
            month += 1

            # Calculate interest
            interest = balance * monthly_rate

            # Determine payment
            if product["product_type"] == "loan":
                payment = product["monthly_payment"]
            else:  # card
                payment = self.calculate_minimum_payment_card(
                    balance, product["min_payment_pct"]
                )

            # Add late fee if applicable (only first month past due)
            late_fee = 0
            if product["days_past_due"] > 0 and month == 1:
                late_fee = product["late_fee_amount"]
                payment += late_fee

            # Ensure payment doesn't exceed balance + interest
            if payment > balance + interest:
                payment = balance + interest

            # Calculate principal payment
            principal_payment = payment - interest - late_fee

            # Update balance
            balance -= principal_payment
            total_paid += payment
            total_interest += interest

            monthly_projection.append(
                {
                    "month": month,
                    "payment": round(payment, 2),
                    "interest": round(interest, 2),
                    "principal": round(principal_payment, 2),
                    "late_fee": round(late_fee, 2),
                    "balance": round(max(balance, 0), 2),
                }
            )

        return {
            "scenario_name": "Minimum Payment",
            "customer_id": product.get("customer_id"),
            "product_id": product["product_id"],
            "product_type": product["product_type"],
            "summary": {
                "original_balance": round(original_balance, 2),
                "total_paid": round(total_paid, 2),
                "total_interest": round(total_interest, 2),
                "months_to_payoff": month,
                "monthly_payment_avg": round(total_paid / month if month > 0 else 0, 2),
            },
            "monthly_projection": monthly_projection,
        }

    def scenario_optimized_payment(self, product: Dict, customer: Dict) -> Dict:
        """Scenario 2: Optimized Payment Strategy"""
        balance = product["balance"]
        original_balance = balance

        # Calculate available cash flow
        available = customer["monthly_income"] - customer["essential_expenses"]
        buffer = available * (customer["income_variability_pct"] / 100)
        safe_allocation = available - buffer

        # Determine interest rate (use penalty rate if past due)
        if product["days_past_due"] > 0:
            annual_rate = product["penalty_rate_pct"]
        else:
            annual_rate = product["annual_rate_pct"]

        monthly_rate = self.calculate_monthly_rate(annual_rate)

        monthly_projection = []
        month = 0
        total_paid = 0
        total_interest = 0

        while balance > 0.01 and month < 600:
            month += 1

            # Calculate interest
            interest = balance * monthly_rate

            # Determine minimum payment
            if product["product_type"] == "loan":
                min_payment = product["monthly_payment"]
            else:
                min_payment = self.calculate_minimum_payment_card(
                    balance, product["min_payment_pct"]
                )

            # Add late fee if applicable
            late_fee = 0
            if product["days_past_due"] > 0 and month == 1:
                late_fee = product["late_fee_amount"]

            # Allocate maximum safe payment (prioritize debt reduction)
            payment = min(safe_allocation, balance + interest + late_fee)
            payment = max(payment, min_payment + late_fee)

            # Calculate principal payment
            principal_payment = payment - interest - late_fee

            # Update balance
            balance -= principal_payment
            total_paid += payment
            total_interest += interest

            monthly_projection.append(
                {
                    "month": month,
                    "payment": round(payment, 2),
                    "interest": round(interest, 2),
                    "principal": round(principal_payment, 2),
                    "late_fee": round(late_fee, 2),
                    "balance": round(max(balance, 0), 2),
                }
            )

        return {
            "scenario_name": "Optimized Payment",
            "customer_id": product.get("customer_id"),
            "product_id": product["product_id"],
            "product_type": product["product_type"],
            "summary": {
                "original_balance": round(original_balance, 2),
                "total_paid": round(total_paid, 2),
                "total_interest": round(total_interest, 2),
                "months_to_payoff": month,
                "monthly_payment_avg": round(total_paid / month if month > 0 else 0, 2),
                "safe_monthly_allocation": round(safe_allocation, 2),
            },
            "monthly_projection": monthly_projection,
        }

    def check_consolidation_eligibility(
        self, product: Dict, customer: Dict
    ) -> Tuple[bool, Optional[Dict], List[str]]:
        """Check if customer is eligible for consolidation offers and track reasons for ineligibility"""
        reasons = []
        for offer in self.offers:
            # Track reasons for this offer
            offer_reasons = []

            # Check product type eligibility
            if product["sub_product_type"] not in offer["product_types_eligible"]:
                offer_reasons.append(
                    f"Product type '{product['sub_product_type']}' not eligible for offer {offer.get('offer_id', '')}."
                )

            # Check conditions
            conditions = offer.get("conditions", {})

            # Check days past due
            if "max_days_past_due" in conditions:
                if product["days_past_due"] > conditions["max_days_past_due"]:
                    offer_reasons.append(
                        f"Days past due {product['days_past_due']} exceeds max allowed {conditions['max_days_past_due']} for offer {offer.get('offer_id', '')}."
                    )

            # Check credit score
            if "min_credit_score" in conditions:
                if customer["credit_score"] < conditions["min_credit_score"]:
                    offer_reasons.append(
                        f"Credit score {customer['credit_score']} is less than required {conditions['min_credit_score']} for offer {offer.get('offer_id', '')}."
                    )

            # If no reasons, this offer is eligible
            if not offer_reasons:
                return True, offer, []

            # Otherwise, collect all reasons for this offer
            reasons.extend(offer_reasons)

        return False, None, reasons

    def scenario_consolidation(self, product: Dict, customer: Dict) -> Dict:
        """Scenario 3: Consolidation Strategy"""
        eligible, offer, reasons = self.check_consolidation_eligibility(
            product, customer
        )

        if not eligible or offer is None:
            return {
                "scenario_name": "Consolidation",
                "customer_id": product.get("customer_id"),
                "product_id": product["product_id"],
                "product_type": product["product_type"],
                "eligible": False,
                "message": "No consolidation offers available for this product",
                "reasons": reasons,
            }

        # Calculate new loan terms
        new_principal = product["balance"]
        new_rate = offer["new_rate_pct"]
        new_term = offer["max_term_months"]
        new_monthly_rate = self.calculate_monthly_rate(new_rate)

        # Calculate monthly payment using amortization formula
        # PMT = P * [r(1+r)^n] / [(1+r)^n - 1]
        if new_monthly_rate > 0:
            new_monthly_payment = (
                new_principal
                * new_monthly_rate
                * math.pow(1 + new_monthly_rate, new_term)
            ) / (math.pow(1 + new_monthly_rate, new_term) - 1)
        else:
            new_monthly_payment = new_principal / new_term

        # Project consolidation payments
        balance = new_principal
        monthly_projection = []
        total_paid = 0
        total_interest = 0

        for month in range(1, new_term + 1):
            interest = balance * new_monthly_rate
            principal_payment = new_monthly_payment - interest
            balance -= principal_payment
            total_paid += new_monthly_payment
            total_interest += interest

            monthly_projection.append(
                {
                    "month": month,
                    "payment": round(new_monthly_payment, 2),
                    "interest": round(interest, 2),
                    "principal": round(principal_payment, 2),
                    "balance": round(max(balance, 0), 2),
                }
            )

        return {
            "scenario_name": "Consolidation",
            "customer_id": product.get("customer_id"),
            "product_id": product["product_id"],
            "product_type": product["product_type"],
            "eligible": True,
            "offer_id": offer["offer_id"],
            "offer_details": {
                "new_rate_pct": new_rate,
                "new_term_months": new_term,
                "original_rate_pct": product["annual_rate_pct"],
            },
            "summary": {
                "original_balance": round(new_principal, 2),
                "total_paid": round(total_paid, 2),
                "total_interest": round(total_interest, 2),
                "months_to_payoff": new_term,
                "monthly_payment": round(new_monthly_payment, 2),
            },
            "monthly_projection": monthly_projection,
        }

    def compare_scenarios(
        self, minimum: Dict, optimized: Dict, consolidation: Dict
    ) -> Dict:
        """Compare all three scenarios and calculate savings"""
        base_cost = minimum["summary"]["total_paid"]
        base_interest = minimum["summary"]["total_interest"]
        base_months = minimum["summary"]["months_to_payoff"]

        comparison = {
            "minimum_payment": {
                "total_paid": base_cost,
                "total_interest": base_interest,
                "months": base_months,
            },
            "optimized_payment": {
                "total_paid": optimized["summary"]["total_paid"],
                "total_interest": optimized["summary"]["total_interest"],
                "months": optimized["summary"]["months_to_payoff"],
                "savings_vs_minimum": {
                    "interest_saved": round(
                        base_interest - optimized["summary"]["total_interest"], 2
                    ),
                    "total_saved": round(
                        base_cost - optimized["summary"]["total_paid"], 2
                    ),
                    "time_saved_months": base_months
                    - optimized["summary"]["months_to_payoff"],
                },
            },
        }

        if consolidation.get("eligible"):
            comparison["consolidation"] = {
                "total_paid": consolidation["summary"]["total_paid"],
                "total_interest": consolidation["summary"]["total_interest"],
                "months": consolidation["summary"]["months_to_payoff"],
                "savings_vs_minimum": {
                    "interest_saved": round(
                        base_interest - consolidation["summary"]["total_interest"], 2
                    ),
                    "total_saved": round(
                        base_cost - consolidation["summary"]["total_paid"], 2
                    ),
                    "time_saved_months": base_months
                    - consolidation["summary"]["months_to_payoff"],
                },
            }
        else:
            comparison["consolidation"] = {"eligible": False}

        return comparison

    def analyze(self, customer_id: str, product_type: str) -> Dict:
        """Run complete analysis for a customer and product"""
        # Get product and customer data
        product = self.get_product_data(customer_id, product_type)
        if product is None:
            return {"error": f"No {product_type} found for customer {customer_id}"}
        # print product data

        product["customer_id"] = customer_id
        customer = self.get_customer_data(customer_id)

        if customer is None:
            return {"error": f"No customer data found for {customer_id}"}

        # Run all three scenarios
        minimum = self.scenario_minimum_payment(product, customer)
        optimized = self.scenario_optimized_payment(product, customer)
        consolidation = self.scenario_consolidation(product, customer)

        # Compare scenarios
        comparison = self.compare_scenarios(minimum, optimized, consolidation)

        result = {
            "customer_id": customer_id,
            "product_type": product_type,
            "product_id": product["product_id"],
            "scenarios": {
                "minimum_payment": minimum,
                "optimized_payment": optimized,
                "consolidation": consolidation,
            },
            "comparison": comparison,
        }

        return self.convert_to_native_types(result)  # type: ignore

    def convert_to_native_types(self, obj):
        """Recursively convert numpy types to native Python types for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self.convert_to_native_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_to_native_types(item) for item in obj]
        elif isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif obj is None:
            return None
        try:
            if pd.isna(obj):
                return None
        except Exception:
            pass
        return obj
