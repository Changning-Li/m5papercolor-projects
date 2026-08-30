# Hardware notes

这里存放 PaperColor 设备级硬件资料、接线记录和实机验证结果。

当前环境监测应用使用的板载资源：

- 内部 I²C：SDA GPIO3、SCL GPIO2
- SHT40：I²C `0x44`
- RX8130CE：I²C `0x32`
- M5PM1：I²C `0x6e`
- 按键 A/B/C：GPIO10、GPIO9、GPIO1
- 屏幕：4 英寸 400×600 Spectra 6 全彩墨水屏
