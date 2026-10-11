import type { Fyo } from 'fyo';
import type { Action, ListViewSettings } from 'fyo/model/types';
import {
  getDocStatusListColumn,
  getStockTransferActions,
} from 'models/helpers';
import { ModelNameEnum } from 'models/types';
import { DeliveryNoteItem } from './DeliveryNoteItem';
import {
  StockTransfer,
  transferFileFields,
  transferFields,
} from './StockTransfer';

export class DeliveryNote extends StockTransfer {
  static override doctype = 'Books Delivery Note';
  static override presentation = {
    label: 'Delivery Note',
    nameField: { label: 'Transfer No', hidden: true },
    fields: transferFields,
    fileFields: transferFileFields,
  };
  static override rowModels = { items: DeliveryNoteItem };
  static override invoiceSchemaName = ModelNameEnum.SalesInvoice;
  static override invoiceMapper = 'make_delivery_note';

  static getListViewSettings(): ListViewSettings {
    return {
      columns: [
        'name',
        getDocStatusListColumn(),
        'party',
        'date',
        'grand_total',
      ],
    };
  }

  static getActions(fyo: Fyo): Action[] {
    return getStockTransferActions(fyo, ModelNameEnum.DeliveryNote);
  }
}
