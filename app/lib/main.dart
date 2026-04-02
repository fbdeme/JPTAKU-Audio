import 'dart:convert';
import 'dart:html' as html;

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:rive/rive.dart' as rive;
import 'package:web_socket_channel/web_socket_channel.dart';

/// Server config
const kServerHost = 'localhost';
const kHttpUrl = 'http://$kServerHost:8080';
const kWsUrl = 'ws://$kServerHost:8765';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await rive.RiveNative.init();
  runApp(const JptakuApp());
}

class JptakuApp extends StatelessWidget {
  const JptakuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JPTAKU - Japanese Tutor',
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.dark(
          primary: Colors.purple.shade300,
          secondary: Colors.pink.shade200,
        ),
      ),
      home: const ChatPage(),
    );
  }
}

// ── BlendShape Mapper ──────────────────────────────────────────────────────

class BlendShapeMapper {
  static Map<String, double> mapToRiveInputs(
      Map<String, dynamic> blendshapes, Set<String> availableInputs) {
    final result = <String, double>{};

    final jaw = (blendshapes['JawOpen'] as num?)?.toDouble() ?? 0;
    final smile = (((blendshapes['MouthSmileLeft'] as num?)?.toDouble() ?? 0) +
            ((blendshapes['MouthSmileRight'] as num?)?.toDouble() ?? 0)) /
        2;
    final frown = (((blendshapes['MouthFrownLeft'] as num?)?.toDouble() ?? 0) +
            ((blendshapes['MouthFrownRight'] as num?)?.toDouble() ?? 0)) /
        2;
    final browUp = (blendshapes['BrowInnerUp'] as num?)?.toDouble() ?? 0;
    final browOuterUp =
        (((blendshapes['BrowOuterUpLeft'] as num?)?.toDouble() ?? 0) +
                ((blendshapes['BrowOuterUpRight'] as num?)?.toDouble() ?? 0)) /
            2;
    final browDown =
        (((blendshapes['BrowDownLeft'] as num?)?.toDouble() ?? 0) +
                ((blendshapes['BrowDownRight'] as num?)?.toDouble() ?? 0)) /
            2;
    final eyeWide =
        (((blendshapes['EyeWideLeft'] as num?)?.toDouble() ?? 0) +
                ((blendshapes['EyeWideRight'] as num?)?.toDouble() ?? 0)) /
            2;

    // ── JcToon Facial Expression Demo (Happy/Sad/Surprised/Angry) ──
    if (availableInputs.contains('Happy')) {
      result['Happy'] = ((smile + jaw * 0.3) * 500).clamp(0, 100);
    }
    if (availableInputs.contains('Sad')) {
      result['Sad'] = (frown * 400).clamp(0, 100);
    }
    if (availableInputs.contains('Surprised')) {
      result['Surprised'] =
          ((browUp + browOuterUp + eyeWide + jaw * 0.8) * 200).clamp(0, 100);
    }
    if (availableInputs.contains('Angry')) {
      result['Angry'] = (browDown * 500).clamp(0, 100);
    }

    // ── Talking Avatar (mouth hight/witdh, kelopakmata, etc.) ──
    if (availableInputs.contains('mouth hight')) {
      // JawOpen → mouth height (0-100)
      result['mouth hight'] = (jaw * 150).clamp(0, 100);
    }
    if (availableInputs.contains('mouth witdh')) {
      // Smile + Funnel → mouth width
      final funnel = (blendshapes['MouthFunnel'] as num?)?.toDouble() ?? 0;
      final pucker = (blendshapes['MouthPucker'] as num?)?.toDouble() ?? 0;
      // Smile = wide, Pucker = narrow → map to width
      result['mouth witdh'] = ((smile * 200 + funnel * 100 - pucker * 50) + 50).clamp(0, 100);
    }
    if (availableInputs.contains('kelopakmata f Slider')) {
      // EyeBlink → eyelid (0=open, 100=closed)
      final blink = (((blendshapes['EyeBlinkLeft'] as num?)?.toDouble() ?? 0) +
              ((blendshapes['EyeBlinkRight'] as num?)?.toDouble() ?? 0)) / 2;
      result['kelopakmata f Slider'] = (blink * 300).clamp(0, 100);
    }
    if (availableInputs.contains('Number 1')) {
      // General expression intensity
      result['Number 1'] = (jaw * 100).clamp(0, 100);
    }

    // ── Direct ARKit mappings for fully custom characters ──
    for (final entry in blendshapes.entries) {
      if (availableInputs.contains(entry.key)) {
        result[entry.key] =
            ((entry.value as num).toDouble() * 100).clamp(0, 100);
      }
    }

    return result;
  }
}

// ── Chat Message Model ─────────────────────────────────────────────────────

class ChatMessage {
  final String text;
  final bool isUser;
  final String? audioUrl;

  ChatMessage({required this.text, required this.isUser, this.audioUrl});
}

// ── Chat Page ──────────────────────────────────────────────────────────────

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  // Rive
  rive.File? _riveFile;
  rive.RiveWidgetController? _riveController;
  final Map<String, rive.NumberInput> _numberInputs = {};

  // WebSocket
  WebSocketChannel? _wsChannel;
  bool _wsConnected = false;

  // Chat
  final List<ChatMessage> _messages = [];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _sending = false;
  String _status = 'Initializing...';

  // Audio (web only — using dart:html)
  html.AudioElement? _audioElement;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await _loadRive();
    _connectWebSocket();
  }

  String _currentRive = 'assets/facial_expression.riv';

  Future<void> _switchRive(String asset) async {
    _riveController?.dispose();
    _riveFile?.dispose();
    _numberInputs.clear();
    _currentRive = asset;
    await _loadRive();
  }

  Future<void> _loadRive() async {
    try {
      final file = await rive.File.asset(
        _currentRive,
        riveFactory: rive.Factory.flutter,
      );
      if (file == null) {
        setState(() => _status = 'Failed to load Rive file');
        return;
      }

      final controller = rive.RiveWidgetController(file);
      final sm = controller.stateMachine;

      // ignore: deprecated_member_use
      for (final input in sm.inputs) {
        if (input is rive.NumberInput) {
          _numberInputs[input.name] = input;
        }
      }

      final inputNames = _numberInputs.keys.join(', ');
      setState(() {
        _riveFile = file;
        _riveController = controller;
        _status = '${_numberInputs.length} inputs: $inputNames';
      });
    } catch (e) {
      setState(() => _status = 'Rive error: $e');
    }
  }

  void _connectWebSocket() {
    try {
      _wsChannel = WebSocketChannel.connect(Uri.parse(kWsUrl));
      setState(() {
        _wsConnected = true;
        _status = 'WS connected';
      });

      _wsChannel!.stream.listen(
        (message) {
          final data = jsonDecode(message as String) as Map<String, dynamic>;
          final type = data['type'] as String? ?? 'unknown';

          if (type == 'chat_response') {
            final audioUrl = '$kHttpUrl${data['audio_url']}';
            _playAudio(audioUrl);
            setState(() => _status = 'Playing audio + animation...');
          } else if (type == 'frame') {
            final blendshapes = data['blendshapes'] as Map<String, dynamic>;
            final mapped = BlendShapeMapper.mapToRiveInputs(
              blendshapes, _numberInputs.keys.toSet());
            for (final entry in mapped.entries) {
              _numberInputs[entry.key]?.value = entry.value;
            }
            final idx = data['index'] as int;
            if (idx % 15 == 0) {
              final active = mapped.entries
                  .where((e) => e.value > 0.5)
                  .map((e) => '${e.key}=${e.value.toStringAsFixed(0)}')
                  .join(', ');
              setState(() => _status = 'Frame $idx | $active');
            }
          } else if (type == 'end') {
            setState(() => _status = 'Done');
            Future.delayed(const Duration(milliseconds: 500), () {
              for (final input in _numberInputs.values) {
                input.value = 0;
              }
            });
          }
        },
        onError: (e) {
          setState(() { _wsConnected = false; _status = 'WS error'; });
          Future.delayed(const Duration(seconds: 5), _connectWebSocket);
        },
        onDone: () {
          setState(() { _wsConnected = false; _status = 'WS closed'; });
          Future.delayed(const Duration(seconds: 5), _connectWebSocket);
        },
      );
    } catch (e) {
      setState(() => _status = 'WS connect error: $e');
    }
  }

  void _playAudio(String url) {
    _audioElement?.pause();
    _audioElement = html.AudioElement(url)..play();
  }

  Future<void> _sendMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty || _sending) return;

    _textController.clear();
    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true));
      _sending = true;
      _status = 'Thinking...';
    });
    _scrollToBottom();

    try {
      final response = await http.post(
        Uri.parse('$kHttpUrl/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _messages.add(ChatMessage(
            text: data['text'],
            isUser: false,
            audioUrl: data['audio_url'],
          ));
          _status = 'Response received, waiting for animation...';
          _sending = false;
        });
      } else {
        setState(() {
          _status = 'Error: ${response.statusCode}';
          _sending = false;
        });
      }
    } catch (e) {
      setState(() {
        _status = 'Network error: $e';
        _sending = false;
      });
    }
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Character area
          Container(
            height: 280,
            color: Colors.grey.shade900,
            child: Stack(
              children: [
                if (_riveController != null)
                  Center(
                    child: SizedBox(
                      width: 250,
                      height: 250,
                      child: rive.RiveWidget(controller: _riveController!),
                    ),
                  )
                else
                  const Center(child: CircularProgressIndicator()),
                // Status bar
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    color: Colors.black54,
                    child: Row(
                      children: [
                        Icon(
                          _wsConnected ? Icons.circle : Icons.circle_outlined,
                          size: 8,
                          color:
                              _wsConnected ? Colors.greenAccent : Colors.red,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            _status,
                            style: const TextStyle(
                                fontSize: 10, fontFamily: 'monospace'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                // Character name + switcher
                Positioned(
                  top: 8,
                  left: 12,
                  right: 12,
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color:
                              Colors.purple.shade900.withValues(alpha: 0.8),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Text(
                          '凛 (Rin)',
                          style: TextStyle(
                              fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const Spacer(),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.black54,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            _charButton('Expression',
                                'assets/facial_expression.riv'),
                            _charButton(
                                'Avatar', 'assets/talking_avatar.riv'),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          // Chat messages
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                return _buildMessageBubble(msg);
              },
            ),
          ),
          // Input area
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey.shade900,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.3),
                  blurRadius: 8,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: SafeArea(
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      decoration: InputDecoration(
                        hintText: 'Type a message in Japanese...',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 10),
                        isDense: true,
                      ),
                      onSubmitted: (_) => _sendMessage(),
                      enabled: !_sending,
                    ),
                  ),
                  const SizedBox(width: 8),
                  FloatingActionButton.small(
                    onPressed: _sending ? null : _sendMessage,
                    child: _sending
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child:
                                CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _charButton(String label, String asset) {
    final isActive = _currentRive == asset;
    return GestureDetector(
      onTap: isActive ? null : () => _switchRive(asset),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isActive ? Colors.purple.shade700 : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(label,
            style: TextStyle(
                fontSize: 10,
                color: isActive ? Colors.white : Colors.white54)),
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage msg) {
    return Align(
      alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: msg.isUser ? Colors.purple.shade700 : Colors.grey.shade800,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(msg.text, style: const TextStyle(fontSize: 15)),
            if (msg.audioUrl != null) ...[
              const SizedBox(height: 4),
              GestureDetector(
                onTap: () => _playAudio('$kHttpUrl${msg.audioUrl}'),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.volume_up,
                        size: 14, color: Colors.purple.shade200),
                    const SizedBox(width: 4),
                    Text('Replay',
                        style: TextStyle(
                            fontSize: 11, color: Colors.purple.shade200)),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _audioElement?.pause();
    _wsChannel?.sink.close();
    _riveController?.dispose();
    _riveFile?.dispose();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}
