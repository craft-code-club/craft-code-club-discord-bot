from typing import Optional
import aiohttp
import logging


logger = logging.getLogger(__name__)

class ImageService:
    async def download_image_bytes(self, image_url: str) -> Optional[bytes]:
        if not image_url:
            return None
        try:
            logger.debug(f'[SERVICES][IMAGE] Downloading image from: {image_url}')

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f'[SERVICES][IMAGE] Failed to download image. Status: {response.status}')
                        return None

                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        logger.warning(f'[SERVICES][IMAGE] Invalid content type: {content_type}')
                        return None

                    # Read image data
                    image_data = await response.read()

                    # Check if we have valid image data
                    if len(image_data) == 0:
                        logger.warning('[SERVICES][IMAGE] Empty image data received')
                        return None

                    # Discord has a file size limit (typically 8MB for regular uploads)
                    if len(image_data) > 8 * 1024 * 1024:  # 8MB
                        logger.warning(f'[SERVICES][IMAGE] Image too large: {len(image_data)} bytes')
                        return None

                    logger.info(f'[SERVICES][IMAGE] Successfully downloaded image: "{image_url}": {len(image_data)} bytes')
                    return image_data

        except aiohttp.ClientError as e:
            logger.warning(f'[SERVICES][IMAGE] Network error downloading image: {e}')
        except Exception as e:
            logger.warning(f'[SERVICES][IMAGE] Unexpected error downloading image: {e}')

        return None

# Global instance
image_service = ImageService()
