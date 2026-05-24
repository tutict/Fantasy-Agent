class TrafficNewsArticleModel {
  final String? title;
  final String? description;
  final String? content;
  final String? url;
  final String? image;
  final DateTime? publishedAt;
  final String? sourceName;
  final String? sourceUrl;

  const TrafficNewsArticleModel({
    this.title,
    this.description,
    this.content,
    this.url,
    this.image,
    this.publishedAt,
    this.sourceName,
    this.sourceUrl,
  });

  factory TrafficNewsArticleModel.fromJson(Map<String, dynamic> json) {
    return TrafficNewsArticleModel(
      title: json['title'],
      description: json['description'],
      content: json['content'],
      url: json['url'],
      image: json['image'],
      publishedAt: json['publishedAt'] != null
          ? DateTime.tryParse(json['publishedAt'])
          : null,
      sourceName: json['sourceName'],
      sourceUrl: json['sourceUrl'],
    );
  }
}
