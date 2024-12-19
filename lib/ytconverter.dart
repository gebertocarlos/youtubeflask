import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';

class YoutubeToMp3Converter extends StatefulWidget {
  const YoutubeToMp3Converter({super.key});

  @override
  _YoutubeToMp3ConverterState createState() => _YoutubeToMp3ConverterState();
}

class _YoutubeToMp3ConverterState extends State<YoutubeToMp3Converter> {
  final TextEditingController _urlController = TextEditingController();
  bool isLoading = false;
  double progress = 0.0;
  String? downloadUrl;

  // Custom colors
  final primaryColor = const Color(0xFF6C63FF); // Modern purple
  final secondaryColor = const Color(0xFF2C3E50); // Dark blue-gray
  final accentColor = const Color(0xFF00B894); // Mint green
  final backgroundColor = const Color(0xFF1A1A2E); // Dark navy
  final cardColor = const Color(0xFF16213E); // Slightly lighter navy

  Future<void> convertVideo() async {
    final youtubeUrl = _urlController.text;

    if (youtubeUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text("Please enter a YouTube URL"),
          backgroundColor: secondaryColor,
          behavior: SnackBarBehavior.floating,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
      return;
    }

    setState(() {
      isLoading = true;
      downloadUrl = null;
      progress = 0.0;
    });

    try {
      for (int i = 0; i <= 100; i++) {
        await Future.delayed(const Duration(milliseconds: 50));
        setState(() {
          progress = i / 100;
        });
      }

      final response = await http.post(
        Uri.parse('http://127.0.0.1:5000/convert'),
        body: {'url': youtubeUrl},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          downloadUrl = data['mp3Link'];
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text("Conversion failed. Please try again."),
            backgroundColor: Colors.red.shade700,
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Error: $e"),
          backgroundColor: Colors.red.shade700,
          behavior: SnackBarBehavior.floating,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Future<void> _launchDownloadUrl() async {
    if (downloadUrl != null) {
      final uri = Uri.parse(downloadUrl!);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
        setState(() {
          _urlController.clear();
          downloadUrl = null;
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text("Could not launch download link."),
            backgroundColor: Colors.red.shade700,
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      }
    }
  }

  Future<void> _pasteClipboardContent() async {
    final clipboardText = await Clipboard.getData('text/plain');
    if (clipboardText != null && clipboardText.text != null) {
      _urlController.text = clipboardText.text!;
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text("Clipboard is empty."),
          backgroundColor: secondaryColor,
          behavior: SnackBarBehavior.floating,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'YouTube to MP3',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        backgroundColor: backgroundColor,
        elevation: 0,
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [backgroundColor, cardColor],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Center(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Card(
                color: cardColor,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                  side: BorderSide(
                      color: primaryColor.withOpacity(0.2), width: 1),
                ),
                elevation: 10,
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.music_note_rounded,
                        size: 48,
                        color: primaryColor,
                      ),
                      const SizedBox(height: 20),
                      Text(
                        'Convert YouTube to MP3',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.9),
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 30),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _urlController,
                              style: const TextStyle(color: Colors.white),
                              decoration: InputDecoration(
                                labelText: 'Paste YouTube URL',
                                labelStyle: TextStyle(
                                  color: Colors.white.withOpacity(0.7),
                                ),
                                prefixIcon: Icon(
                                  Icons.link_rounded,
                                  color: primaryColor,
                                ),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(15),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderSide: BorderSide(
                                    color: Colors.white.withOpacity(0.3),
                                  ),
                                  borderRadius: BorderRadius.circular(15),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderSide: BorderSide(color: primaryColor),
                                  borderRadius: BorderRadius.circular(15),
                                ),
                                filled: true,
                                fillColor: backgroundColor.withOpacity(0.5),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          ElevatedButton(
                            onPressed: _pasteClipboardContent,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: primaryColor,
                              padding: const EdgeInsets.all(15),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(15),
                              ),
                              elevation: 5,
                            ),
                            child: const Icon(Icons.content_paste_rounded),
                          ),
                        ],
                      ),
                      const SizedBox(height: 30),
                      if (isLoading)
                        Column(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(10),
                              child: LinearProgressIndicator(
                                value: progress,
                                backgroundColor: backgroundColor,
                                color: primaryColor,
                                minHeight: 8,
                              ),
                            ),
                            const SizedBox(height: 15),
                            Text(
                              '${(progress * 100).toStringAsFixed(0)}%',
                              style: TextStyle(
                                color: primaryColor,
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      if (downloadUrl == null && !isLoading)
                        ElevatedButton(
                          onPressed: convertVideo,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: primaryColor,
                            padding: const EdgeInsets.symmetric(
                              horizontal: 50,
                              vertical: 20,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(15),
                            ),
                            elevation: 5,
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.start),
                              SizedBox(width: 10),
                              Text(
                                'Convert',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                      if (downloadUrl != null)
                        ElevatedButton(
                          onPressed: _launchDownloadUrl,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: accentColor,
                            padding: const EdgeInsets.symmetric(
                              horizontal: 50,
                              vertical: 20,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(15),
                            ),
                            elevation: 5,
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.download_rounded),
                              SizedBox(width: 10),
                              Text(
                                'Download MP3',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
