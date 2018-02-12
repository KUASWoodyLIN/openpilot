## 儀表板

- [Dashboard](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/dashboard/Dashboard.py) : 打印油門、煞車、轉向、速度、加速度等等在shell上

- [Dashboard plt](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/dashboard/Dashboard_plt.py) : 圖表方式顯示油門、煞車、轉向、速度、加速度等等

- [Keyboard](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/dashboard/keyboard.py) : w, a, s, d 控制汽車油門、煞車、轉向

- [Keyboard v2](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/dashboard/keyboard2.py) : 盡量始油門、煞車、轉向控制成線性 (須在優化)

- [KeyboardCatcher](./keyboardCatcher/) : Directory

  - [KeyboardCatcher.py](./keyboardCatcher/keyboardCatcher.py) : 擷取鍵盤w, a, s, d 按鈕類別

  ​

## Zmq & Capnp 測試

- [Sub](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/dashboard/vision_sub.py) : 接收訊息
- [Pub](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/dashboard/vision_pub.py) : 發布訊息

以vision 傳輸為例：

Port : 定義於[service_list.yaml](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/selfdrive/service_list.yaml#L67)

```vision: [8041, true]```

Data : 定義於[log.capnp](https://github.com/KUASWoodyLIN/openpilot/blob/linux_env/cereal/log.capnp#L1380) 

```
struct VisionData {
  dRel @0 :Float32;
  yRel @1 :Float32;
  vRel @2 :Float32;
  aRel @3 :Float32;
  vLead @4 :Float32;
  aLead @5 :Float32;
  dPath @6 :Float32;
  vLat @7 :Float32;
  vLeadK @8 :Float32;
  aLeadK @9 :Float32;
  fcw @10 :Bool;
  status @11 :Bool;
}
```





