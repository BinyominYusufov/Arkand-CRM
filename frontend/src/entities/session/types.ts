export interface SessionBusiness {
  id: number;
  name: string;
  code: string;
  kind: string;
  kind_display?: string;
  is_active: boolean;
}

export interface Me {
  id: number;
  email: string;
  username: string;
  full_name: string;
  phone: string;
  role: string;
  business: SessionBusiness | null;
  businesses: SessionBusiness[];
  permissions: string[];
  cash_register_ids: number[];
}
