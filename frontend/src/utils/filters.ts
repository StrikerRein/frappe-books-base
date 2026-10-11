import { ModelNameEnum } from 'models/types';
import type { Filter } from 'src/frappe/api';

export const routeFilters = {
  PurchasePayments: [['reference_type', '=', ModelNameEnum.PurchaseInvoice]],
  SalesPayments: [['reference_type', '=', ModelNameEnum.SalesInvoice]],
  Suppliers: [['role', 'in', ['Supplier', 'Both']]],
  Customers: [['role', 'in', ['Customer', 'Both']]],
} satisfies Record<string, Filter[]>;

export const createFilters = {
  PurchasePayments: { payment_type: 'Pay' },
  SalesPayments: { payment_type: 'Receive' },
  Suppliers: { role: 'Supplier' },
  Customers: { role: 'Customer' },
  Party: { role: 'Both' },
};
