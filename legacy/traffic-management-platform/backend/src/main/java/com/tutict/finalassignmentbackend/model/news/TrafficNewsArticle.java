package com.tutict.finalassignmentbackend.model.news;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class TrafficNewsArticle {

    private String title;
    private String description;
    private String content;
    private String url;
    private String image;
    private String publishedAt;
    private String sourceName;
    private String sourceUrl;
}
