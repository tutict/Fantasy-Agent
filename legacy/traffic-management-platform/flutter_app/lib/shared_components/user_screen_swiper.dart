import 'package:card_swiper/card_swiper.dart';
import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class UserScreenSwiper extends StatelessWidget {
  const UserScreenSwiper({
    required this.onPressed,
    super.key,
  });

  final Function() onPressed;

  @override
  Widget build(BuildContext context) {
    final double screenWidth = MediaQuery.of(context).size.width;
    final double screenHeight = MediaQuery.of(context).size.height;

    double viewportFraction;
    double scale;
    if (screenWidth < 600) {
      viewportFraction = 0.85;
      scale = 0.9;
    } else if (screenWidth < 1000) {
      viewportFraction = 0.75;
      scale = 0.85;
    } else {
      viewportFraction = 0.6;
      scale = 0.75;
    }

    final double aspectRatio = screenWidth < 600 ? 3 / 2 : 16 / 9;
    double swiperHeight = screenWidth * viewportFraction / aspectRatio;
    swiperHeight = swiperHeight.clamp(150.0, screenHeight * 0.45);

    final List<String> imageUrls = [
      ImageRasterPath.liangnv1,
      ImageRasterPath.liangnv2,
      ImageRasterPath.liangnv3,
    ];

    final List<String> safetySlogans = [
      'shared.userScreenSwiper.slogan.safeDriving'.tr,
      'shared.userScreenSwiper.slogan.followRules'.tr,
      'shared.userScreenSwiper.slogan.slowDown'.tr,
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32.0, horizontal: 16.0),
      child: SizedBox(
        height: swiperHeight,
        child: Swiper(
          itemBuilder: (BuildContext context, int index) {
            return GestureDetector(
              onTap: onPressed,
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16.0),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.2),
                      offset: const Offset(0, 4),
                      blurRadius: 8,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16.0),
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Image.asset(
                        imageUrls[index],
                        fit: BoxFit.cover,
                      ),
                      Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [
                              Colors.black.withValues(alpha: 0.5),
                              Colors.transparent,
                            ],
                            begin: Alignment.bottomCenter,
                            end: Alignment.center,
                          ),
                        ),
                      ),
                      Positioned(
                        bottom: 16.0,
                        left: 16.0,
                        right: 16.0,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12.0,
                            vertical: 8.0,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.6),
                            borderRadius: BorderRadius.circular(8.0),
                          ),
                          child: Text(
                            safetySlogans[index],
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                            textAlign: TextAlign.center,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
          itemCount: imageUrls.length,
          pagination: const SwiperPagination(
            builder: RectSwiperPaginationBuilder(
              activeColor: Colors.blueAccent,
              color: Colors.grey,
              size: Size(10.0, 2.0),
              activeSize: Size(20.0, 2.0),
            ),
          ),
          control: const SwiperControl(
            color: Colors.blueAccent,
            size: 24.0,
          ),
          autoplay: true,
          autoplayDelay: 3000,
          viewportFraction: viewportFraction,
          scale: scale,
          fade: 0.8,
          duration: 500,
        ),
      ),
    );
  }
}
