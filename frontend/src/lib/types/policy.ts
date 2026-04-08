export interface IAddress {
  street: string;
  city: string;
  state: string;
  zipCode: string;
}

export interface IDrivingHistory {
  accidentCount: number;
  violationCount: number;
  yearsLicensed: number;
}

export interface IDriverInput {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  licenseNumber: string;
  address: IAddress;
  drivingHistory: IDrivingHistory;
}

export interface IVehicleInput {
  make: string;
  model: string;
  year: number;
  vin: string;
  mileage: number;
}

export interface IQuoteCreateRequest {
  vehicle: IVehicleInput;
  driver: IDriverInput;
  coverageType: 'basic' | 'full';
}

export interface IPremiumBreakdownItem {
  factor: string;
  value: string;
  impact: number;
}

export interface IQuoteResponse {
  id: number;
  premiumAmount: number;
  coverageType: string;
  status: string;
  premiumBreakdown: IPremiumBreakdownItem[];
  vehicleMake: string;
  vehicleModel: string;
  vehicleYear: number;
  expiresAt: string;
  createdAt: string;
}

export interface IQuoteSummary {
  id: number;
  coverageType: string;
  premiumAmount: number;
  status: string;
  vehicleSummary: string;
  createdAt: string;
}

export interface IPolicyResponse {
  id: number;
  policyNumber: string;
  quoteId: number;
  status: string;
  coverageType: string;
  premiumAmount: number;
  effectiveDate: string;
  expirationDate: string;
  renewedFromPolicyId: number | null;
  renewedToPolicyId: number | null;
  createdAt: string;
}

export interface IPolicySummary {
  id: number;
  policyNumber: string;
  coverageType: string;
  premiumAmount: number;
  status: string;
  vehicleSummary: string;
  effectiveDate: string;
  expirationDate: string;
}

export interface IPaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface IAdminPolicyItem {
  id: number;
  policyNumber: string;
  customerName: string;
  vehicleSummary: string;
  coverageType: string;
  premiumAmount: number;
  status: string;
  effectiveDate: string;
  expirationDate: string;
}

export interface IAdminPolicyListResponse {
  items: IAdminPolicyItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface IPolicyActionResponse {
  id: number;
  policyNumber: string;
  status: string;
  effectiveDate: string;
  expirationDate: string;
  cancellationReason: string | null;
  cancellationDate: string | null;
  reinstatementReason: string | null;
  reinstatementDate: string | null;
  renewedFromPolicyId: number | null;
  updatedAt: string;
}

// V3 — Renewal Types

export interface IExpiringPolicyItem {
  id: number;
  policyNumber: string;
  coverageType: string;
  premiumAmount: number;
  expirationDate: string;
  daysUntilExpiry: number;
}

export interface IExpiringPoliciesResponse {
  items: IExpiringPolicyItem[];
}

export interface IPremiumBreakdownItem {
  factor: string;
  value: string;
  impact: number;
}

export interface IRenewalPreviewResponse {
  policyId: number;
  policyNumber: string;
  currentPremium: number;
  renewalPremium: number;
  premiumDifference: number;
  premiumBreakdown: IPremiumBreakdownItem[];
  coverageType: string;
  effectiveDate: string;
  expirationDate: string;
}

export interface IRenewalPolicyResponse {
  id: number;
  policyNumber: string;
  quoteId: number;
  status: string;
  coverageType: string;
  premiumAmount: number;
  effectiveDate: string;
  expirationDate: string;
  renewedFromPolicyId: number | null;
  renewedToPolicyId: number | null;
  vehicleMake: string | null;
  vehicleModel: string | null;
  vehicleYear: number | null;
  vehicleVin: string | null;
  driverFirstName: string | null;
  driverLastName: string | null;
  createdAt: string;
}

// V4 — Risk Rules Types

export interface IBracketItem {
  condition: string;
  adjustment: number;
}

export interface IRiskRuleResponse {
  id: number;
  factorName: string;
  label: string;
  isEnabled: boolean;
  brackets: IBracketItem[];
  createdAt: string;
  updatedAt: string;
}

export interface IRiskRuleListResponse {
  items: IRiskRuleResponse[];
}

export interface IRiskRuleCreateRequest {
  factorName: string;
  label: string;
  brackets: IBracketItem[];
}

export interface IRiskRuleUpdateRequest {
  label?: string;
  brackets?: IBracketItem[];
}
