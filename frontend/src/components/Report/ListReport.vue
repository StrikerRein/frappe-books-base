<template>
  <div class="overflow-hidden flex flex-col h-full">
    <ClientReviewAssignment v-if="report.reportName === 'general-ledger'" :items="reviewSelection.map(name => ({ kind: 'ledger', name }))" @clear="reviewSelection = []" />
    <FrappeScrollArea
      v-if="dataSlice.length"
      orientation="both"
      class="min-h-0 flex-1"
      viewport-class="px-3 pb-10 sm:px-5"
    >
      <FrappeList
        ref="list"
        :columns="listColumns"
        :row-height="40"
        divider="full"
        class="-mx-3 text-base tabular-nums list-gap-4 list-row-px-3"
      >
        <FrappeListHeader class="sticky top-0 z-10 min-w-max bg-surface-base">
          <ReportColumnHeader
            v-for="(column, index) in report.columns"
            :key="column.fieldname"
            :ref="(header) => (columnHeaders[column.fieldname] = header)"
            :label="column.label"
            :width="columnWidths.get(column)"
            :direction="languageDirection"
            :class="getAlignmentClass(column)"
            @resize="columnWidths.set(column.fieldname, $event)"
            @commit="columnWidths.set(column.fieldname, $event, true)"
            @fit="fitColumn(column, index)"
          />
        </FrappeListHeader>

        <FrappeListRows :items="dataSlice" :row-key="getRowKey">
          <template #default="{ item: row, index, value }">
            <FrappeListRow
              v-if="!row.folded"
              :value="value"
              :on-click="getRowAction(row, index)"
            >
              <FrappeListCell
                v-for="(cell, cellIndex) in row.cells"
                :key="`${cellIndex}-${index}-cell`"
                class="min-w-0"
                :class="[
                  getCellColorClass(cell, row),
                  getCellTypeClass(cell, row),
                  getAlignmentClass(cell),
                ]"
                :style="getIndentStyle(cell)"
              >
                <input v-if="report.reportName === 'general-ledger' && cellIndex === 0 && row.reviewEntry && !row.isSummary" v-model="reviewSelection" type="checkbox" :value="row.reviewEntry" :aria-label="`Select ledger item ${cell.value} for client review`" :disabled="!reviewSelection.includes(row.reviewEntry) && reviewSelection.length >= 50" class="mr-2 shrink-0" @click.stop />
                <button
                  v-if="
                    row.isGroup &&
                    cellIndex === 0 &&
                    getAccountLedgerLink(report, row)
                  "
                  type="button"
                  class="me-1 shrink-0 rounded-1 p-1 hover:bg-surface-gray-2"
                  :aria-expanded="!row.foldedBelow"
                  :aria-label="
                    row.foldedBelow
                      ? t`Expand ${cell.value}`
                      : t`Collapse ${cell.value}`
                  "
                  @click.stop="onRowClick(row, index)"
                >
                  <FrappeIcon
                    :icon="
                      row.foldedBelow
                        ? 'lucide-chevron-right'
                        : 'lucide-chevron-down'
                    "
                    class="size-3.5"
                  />
                </button>
                <RouterLink
                  v-if="
                    getAccountLedgerLink(report, row, report.columns[cellIndex])
                  "
                  :to="
                    getAccountLedgerLink(
                      report,
                      row,
                      report.columns[cellIndex]
                    ) ?? ''
                  "
                  class="block w-full min-w-0 rounded-1 hover:underline focus-visible:outline focus-visible:outline-2"
                  :title="
                    report.reportName === 'general-ledger'
                      ? t`View original bank transaction`
                      : t`View transactions in General Ledger`
                  "
                  @click.stop
                >
                  <ReportOverflowText :value="cell.value" />
                </RouterLink>
                <ReportOverflowText v-else :value="cell.value" />
              </FrappeListCell>
            </FrappeListRow>
          </template>
        </FrappeListRows>
      </FrappeList>
    </FrappeScrollArea>
    <FrappeLoadingText
      v-else-if="report.loading"
      class="mt-20 w-full justify-center"
      :text="t`Loading Report...`"
    />
    <p v-else class="px-3 py-10 text-center text-p-sm text-ink-gray-4">
      {{ t`No values to be displayed` }}
    </p>

    <!-- Pagination Footer -->
    <div v-if="report.usePagination" class="mt-auto flex-shrink-0">
      <Paginator
        ref="paginator"
        :item-count="entryRowIndexes.length"
        class="px-3 sm:px-5"
        @index-change="setPageIndices"
      />
    </div>
  </div>
</template>
<script>
import {
  Icon as FrappeIcon,
  LoadingText as FrappeLoadingText,
  ScrollArea as FrappeScrollArea,
} from 'frappe-ui';
import { Report } from 'reports/Report';
import ClientReviewAssignment from 'src/components/ClientReviewAssignment.vue';
import {
  List as FrappeList,
  ListCell as FrappeListCell,
  ListHeader as FrappeListHeader,
  ListRow as FrappeListRow,
  ListRows as FrappeListRows,
} from 'frappe-ui/list';
import { isEqual } from 'lodash';
import { isNumeric } from 'src/utils';
import { languageDirectionKey } from 'src/utils/injectionKeys';
import { defineComponent, inject } from 'vue';
import { RouterLink } from 'vue-router';
import { routeTo } from 'src/utils/ui';
import { getAccountLedgerLink } from './accountLedgerLink';
import Paginator from '../Paginator.vue';
import ReportColumnHeader from './ReportColumnHeader.vue';
import { getReportCellColorClass } from './cellColor';
import { ReportColumnWidths } from './ReportColumnWidths';
import ReportOverflowText from './ReportOverflowText.vue';

export default defineComponent({
  components: {
    ClientReviewAssignment,
    FrappeIcon,
    RouterLink,
    FrappeLoadingText,
    FrappeList,
    FrappeListCell,
    FrappeListHeader,
    ReportColumnHeader,
    ReportOverflowText,
    FrappeListRow,
    FrappeListRows,
    FrappeScrollArea,
    Paginator,
  },
  props: {
    report: Report,
  },
  setup() {
    return {
      languageDirection: inject(languageDirectionKey),
    };
  },
  data() {
    return {
      columnWidths: new ReportColumnWidths(this.report.reportName),
      columnHeaders: {},
      reviewSelection: [],
      pageStart: 0,
      pageEnd: 0,
    };
  },
  computed: {
    dataSlice() {
      if (this.report?.usePagination) {
        return this.report.reportData.slice(
          this.getPageRow(this.pageStart),
          this.getPageRow(this.pageEnd)
        );
      }

      return this.report.reportData;
    },
    entryRowIndexes() {
      return this.report.reportData.flatMap((row, index) =>
        row.isEmpty || row.isSummary ? [] : [index]
      );
    },
    listColumns() {
      return this.report.columns.map(
        (column) => `${this.columnWidths.get(column)}px`
      );
    },
  },
  watch: {
    'report.filterMap'(filters, previousFilters) {
      if (!isEqual(filters, previousFilters)) {
        this.reviewSelection = [];
        this.$refs.paginator?.setPageNo(1);
      }
    },
    'report.reportName'(name) {
      this.reviewSelection = [];
      this.columnWidths = new ReportColumnWidths(name);
    },
  },
  methods: {
    getAccountLedgerLink,
    getRowAction(row, index) {
      if (row.isGroup) return () => this.onRowClick(row, index);
      const link = getAccountLedgerLink(this.report, row);
      return link ? () => routeTo(link) : undefined;
    },
    fitColumn(column, index) {
      this.columnWidths.fit(
        column,
        index,
        this.report.reportData,
        this.columnHeaders[column.fieldname].$el,
        this.$refs.list.$el
      );
    },
    /** Where a page starting at this entry starts; the last page keeps the rows after it. */
    getPageRow(entry) {
      return entry
        ? (this.entryRowIndexes[entry] ?? this.report.reportData.length)
        : 0;
    },
    getRowKey(row, index) {
      return `${index}-${row.cells?.[0]?.value ?? ''}`;
    },
    setPageIndices({ start, end }) {
      this.pageStart = start;
      this.pageEnd = end;
    },
    onRowClick(clickedRow, r) {
      if (!clickedRow.isGroup) {
        return;
      }

      r += 1;
      clickedRow.foldedBelow = !clickedRow.foldedBelow;
      const folded = clickedRow.foldedBelow;
      let row = this.dataSlice[r];

      while (row && row.level > clickedRow.level) {
        row.folded = folded;
        r += 1;
        row = this.dataSlice[r];
      }
    },
    getIndentStyle(cell) {
      return cell.indent
        ? { paddingInlineStart: `${cell.indent * 2}rem` }
        : undefined;
    },
    getCellTypeClass(cell, row) {
      const italics = cell.italics ? 'italic' : '';
      if (row.isGroup) {
        return [cell.bold ? 'text-sm-bold' : 'text-sm-semibold', italics];
      }
      return [cell.bold ? 'text-base-bold' : '', italics];
    },
    getAlignmentClass(cell) {
      if (this.languageDirection === 'rtl') {
        return 'justify-end text-end';
      }

      const alignment =
        cell.align ?? (isNumeric(cell.fieldtype) ? 'right' : 'left');
      if (alignment === 'right') {
        return 'justify-end text-end';
      }
      if (alignment === 'center') {
        return 'justify-center text-center';
      }
      return 'justify-start text-start';
    },
    getCellColorClass(cell, row) {
      const precision = this.fyo.singles.SystemSettings?.display_precision ?? 2;
      return getReportCellColorClass(cell, precision, row.isGroup);
    },
  },
});
</script>
