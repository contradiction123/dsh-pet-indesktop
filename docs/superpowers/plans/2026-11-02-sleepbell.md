# 睡铃雪影娃娃接入计划

**Goal:** 用用户已确认的细腻插画造型替换默认角色，增加四组独立待机。

**Architecture:** 复用 MovieLibrary / FrameSeqClip 和现有透明窗口、交互与多平台分支；角色原生 RGBA 素材单独标记，不冒充白底反解产物。使用固定比例高清画布，不按帧重新对齐脚底。

**Tech Stack:** PySide6、透明 PNG、无损 WebP。

**Spec:** 本次聊天已确认的造型预览及四组待机（眨眼呼吸、歪头张望、轻晃铃铛、困倦打哈欠）。

相关既有流程：[素材流水线](../../ASSET-PIPELINE.md)、[无源角色包](../../PR-REPORT-ASSET-ARCH-LOSSLESS-2026-10-19.md)、[文档索引](../../INDEX.md)。本次使用原生 RGBA，不执行旧视频的白底反解。

## Global Constraints

- 保留已有角色文件；默认角色改为 sleepbell。
- 不安装依赖，不提交推送，不运行应用、测试、构建或检查器。
- 不改本机已有用户配置；保存过的角色选择仍优先于默认值。
- 不接 Codex 状态；生成素材需检查跨帧一致性和边缘。

## Review Focus

- 新角色发现、缺帧拒收与原生透明处理链身份。
- 旧素材不含逐帧时长时保持固定 FPS。
- 变速、暂停、末帧停留与异步到货后的计时。
- 画布比例、固定锚点、左右移动方向。
- 新默认与已有角色选择的区别，双平台运行未验证。

## Tasks

- [x] 生成并查看四组高清待机图集，保存原件与制作来源。
- [x] 转换成固定画布的无损帧序列；为缺少专用美术的交互明确兜底。
- [x] 扩展 FrameSeqClip 的可选 durations_ms，并保留旧固定 FPS 路径。
- [x] 在角色包身份、发现和默认选择处接入 sleepbell，更新素材署名。
- [x] 只读复核差异，记录未验证项和用户可执行的验证命令。

## 实施记录与边界

- 角色资源：`assets/characters/sleepbell/`，7 张源图（含确认的母版），
  8 个 clip、43 张 1280×720 运行帧、WebP 合计 11,876,878 字节；整个目录约 29 MiB。
  四种待机 GIF 位于 `previews/`，仅供观察，不用于生产播放。
- 新增 `tools/import_sleepbell.py`：复用 `pack_download.frame_digest` 的身份算法，
  固定格子拆帧、无损编码，输出索引、几何和动作侧车。使用已有的 bundled Pillow，未安装依赖。
- `catalog.py`：默认改为 sleepbell，保留原角色；内置原生包解析到包根，
  保证索引、几何和实际加载使用相同根。已有配置的明确角色选择不迁移。
- `character_pack.py` / `library.py`：安装闭包和运行采纳共用处理链编码身份，
  接受原生透明 RGBA，不伪造白底反解标记。
- `frameseq_clip.py`：有效 durations_ms 使用逐帧停留、累计时间和变速；
  实际上屏后重设该帧间隔，缺失或无效整表回退原固定 FPS。
- 三个相关测试文件补充回归用例，**未运行**；未运行应用、测试、构建、lint、
  格式化、类型检查或静态分析器，未提交或推送。后续环境配置与打包记录见下节。
- 白底合成图确认透明底有效。四组待机以外补了走路与挥手；
  转向为短暂中性姿势，拖拽使用待机。专门跳跃、落地和 16 方向视线尚未重绘。
- 运行 CPU、实际内存与双平台交互均未实测，不能认定已通过验收。
  1280×720 RGBA 单帧理论解码缓冲 3,686,400 字节（不含 Qt 对象、缓存和预取），
  高清化的内存成本需要实机确认。没有新增运行线程或网络功能。

本次是制作与源码接入；素材的跨帧细节、动作切换、缩放清晰度仍需实机检查。
原始交接包没有覆盖，原角色资源没有删除；只调整默认选择。

## 2026-11-02 环境配置、macOS 打包与启动

用户明确要求「打包启动」「帮我配置环境」后，在项目 `.venv/` 安装
`requirements.txt` 和 PyInstaller；没有安装到系统 Python。`.venv/` 已加入忽略。
依赖清单快照在 `build/environment-macos.txt`；`pip check` 输出
`No broken requirements found.`。

补齐两处实际打包接线：`make_icon.py` 从无源包索引的待机 WebP 提取首帧，
继续复用原有图标装配；`check_frameseq_bundle.py` 对原生角色包使用索引采纳规则，
不再漏检没有 videos/ 的角色。原角色 106 段缓存调用既有 `convert_clip` 生成，
未更改编码档或反解算法。

构建命令：`PYTHON_BIN="$PWD/.venv/bin/python" bash scripts/build_macos.sh --variants webm`。
真实结果：退出码 0；114 段素材完整性检查通过，包内 OCR 模块/模型/配置、
TTS 依赖、UTF-8 编码、桥接零依赖检查均通过；完成本机 ad-hoc 签名。
完整日志在 `build/build-macos-sleepbell.log`，缓存日志在
`build/prepare-character-cache.log`。

产物：`build/macos/dsh-pet-standalone-webm.app`（约 2.1 GiB）。
通过 `open -n` 启动，确认打包进程存活；Computer Use 原生应用截图中已看到娃娃。
这证明 macOS 构建与首屏显示，不代表拖拽/缩放/全部动作或 Windows 已验收。
未运行 pytest、lint 或格式化工具；原建议测试命令仍待执行。

## 2026-11-02 切换角色后停播修复

用户报告菜单切换后画面停止。原进程 57695 的采样显示主线程仍在 Qt 事件循环，
不是死锁；日志停在 T2 静止档。重启并捕获 stderr 后，经档案热更新切换角色复现：
`PetSprite.bind_clip → old_clip.stop → QTimer.stop` 抛出
`RuntimeError: libshiboken: Internal C++ object (PySide6.QtCore.QTimer) already deleted.`。
切库代码已销毁旧 QObject 库，但 sprite 留着旧 clip，下一次绑定才停止它，生命周期顺序错误。

`pet/pet_sprite.py` 将已有 `library` 属性改为受控 setter：换库前停旧 clip、
断开旧信号并清绑定，保留最后画面与宿主回调；主宠、子宠、档案热更新共用。
`tests/test_pet_sprite.py` 新增真实 QTimer 销毁后的再绑定回归用例，未运行。

重新执行 macOS 打包，退出码 0；日志在 `build/build-macos-switch-fix.log`。
修复版进程 92879 经档案热更新执行 `sleepbell → shenshen → sleepbell`，
原角色和娃娃切换后都有持续 T1 动画/T0 漫游记录，运行错误输出中的
`Internal C++ object` 为 0；当前保留 sleepbell。这覆盖真实应用热切换路径，
没有声称已自动点击验收全部菜单。诊断 stderr 分别保留于
`build/pet-switch-runtime.log`（修复前）和 `build/pet-switch-fixed-runtime.log`（修复后）。

建议执行的新增回归：
`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_pet_sprite.py tests/test_overlay_app_hosts.py tests/test_overlay_profile_reset.py`。

## 2026-11-02 待机漂移与走路脸型修订（motion-v2）

用户要求修复录屏中确认的待机不连贯和走路脸部异常。前一版歪头第 4 帧鞋底
横移 23 源像素；哈欠横移范围 29 源像素，不同待机起始落脚高度差达 15 源像素。
走路另外生成了三分之二侧转脸，偏离确认的母版。

- 新增 `sources/{tilt,yawn,walk}-{a,b}-v2.png`，每组十二个姿态；
  走路使用固定正面脸型，歪头小幅递进，哈欠逐步开闭眼与嘴。
  老 `sources/*.png` 仍保留作历史源，装配器优先读取配对 v2 图集。
- `tools/import_sleepbell.py`：对每个动作只算一次缩放；站立素材按已检查过的
  鞋底登记，走路保留整组固定原点。待机/拖拽/转向共用同一首尾中性帧，
  重新安排运动段时长。白底反解链、运行线程和播放器代码没有改动。
- 四组待机的鞋底横纵跨度均为 0 源像素，首尾 RGBA 完全一致。
  输出共 8 clip / 61 帧；走路周期仍为 840ms（6×140 → 12×70），步幅仍 80。
  这保持位移速度，但走路期间的解码频率会增加，CPU/内存增量没有专门测量。
- 素材登记测量在 `build/sleepbell-motion-v2/registration-report.json`；
  旧版本完整备份在该目录 `before/`；`sources/motion-v2.json` 保存修订来源。
- 已重新打包 macOS，退出码 0；所有包内硬门通过，日志
  `build/build-macos-motion-v2.log`。进程 19933 已运行并持续推进动画。
- 录得 44.98 秒真实桌宠窗口视频 `build/sleepbell-motion-v2/live-motion-v2.mov`；
  前段未捕获到角色，25～44.8 秒可见，放大裁切为
  `motion-v2-screen-closeup.mp4`；原点固定裁切，没有跟随角色或抹掉位移。
  `live-v2-contact-sheet.jpg` 是录屏抽帧，`walk-frames-v2.jpg` 是运行素材逐帧图。
  实录可见待机脚底保持、走路脸型保持正面，完整主观观感仍由用户确认。
- 同步调整已存在的眨眼时长断言为 2.700 秒；未执行 pytest/lint/格式化，
  不声称测试套件通过。建议：
  `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_library_sourceless.py tests/test_frameseq_clip.py`。

## 验证（仅建议，由用户决定执行）

`QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_character_pack.py tests/test_library_sourceless.py tests/test_frameseq_clip.py`

`python -m pet`：检查默认角色、四种待机、缩放、点击、拖拽及暂停恢复；macOS 与 Windows 分别验收。
