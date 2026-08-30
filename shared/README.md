# Shared code

这里存放至少被两个 PaperColor 应用使用的稳定共用代码，例如硬件抽象、显示组件或通用驱动。

在只有一个应用使用某段代码时，先把它留在该应用内部，避免过早抽象。以后提取 PlatformIO 共用库时，建议放在 `shared/lib/<library-name>/`，并由应用通过 `lib_extra_dirs` 引用。
