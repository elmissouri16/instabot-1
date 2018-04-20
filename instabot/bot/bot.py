import atexit
import datetime
import signal

from ..api import API
from .bot_archive import archive, archive_medias, unarchive_medias
from .bot_block import block, block_bots, block_users, unblock, unblock_users
from .bot_checkpoint import load_checkpoint, save_checkpoint
from .bot_comment import (comment, comment_geotag, comment_hashtag,
                          comment_medias, comment_user, comment_users,
                          is_commented)
from .bot_delete import delete_comment, delete_media, delete_medias
from .bot_direct import (send_hashtag, send_like, send_media, send_medias,
                         send_message, send_messages, send_profile)
from .bot_filter import (check_media, check_not_bot, check_user, filter_medias,
                         filter_users)
from .bot_follow import (follow, follow_followers, follow_following,
                         follow_users)
from .bot_get import (convert_to_user_id, get_archived_medias, get_comment,
                      get_geotag_medias, get_geotag_users, get_hashtag_medias,
                      get_hashtag_users, get_locations_from_coordinates,
                      get_media_commenters, get_media_comments,
                      get_media_id_from_link, get_media_info, get_media_likers,
                      get_media_owner, get_popular_medias, get_timeline_medias,
                      get_timeline_users, get_total_hashtag_medias,
                      get_total_user_medias, get_user_followers,
                      get_user_following, get_user_info, get_user_likers,
                      get_user_medias, get_user_id_from_username,
                      get_username_from_user_id, get_your_medias, search_users)
from .bot_like import (like, like_followers, like_following, like_geotag,
                       like_hashtag, like_medias, like_timeline, like_user,
                       like_users)
from .bot_photo import download_photo, download_photos, upload_photo
from .bot_stats import save_user_stats
from .bot_support import (add_blacklist, add_whitelist, check_if_file_exists,
                          check_whitelists, console_print, extract_urls,
                          read_list_from_file)
from .bot_unfollow import (unfollow, unfollow_everyone, unfollow_non_followers,
                           unfollow_users, update_unfollow_file)
from .bot_unlike import unlike, unlike_medias, unlike_user
from .bot_video import upload_video


class Bot(object):
    def __init__(self,
                 whitelist=False,
                 blacklist=False,
                 comments_file=False,
                 proxy=None,
                 max_likes_per_day=1000,
                 max_unlikes_per_day=1000,
                 max_follows_per_day=350,
                 max_unfollows_per_day=350,
                 max_comments_per_day=100,
                 max_blocks_per_day=100,
                 max_unblocks_per_day=100,
                 max_likes_to_like=100,
                 max_messages_per_day=300,
                 filter_users=True,
                 filter_business_accounts=True,
                 filter_verified_accounts=True,
                 max_followers_to_follow=2000,
                 min_followers_to_follow=10,
                 max_following_to_follow=2000,
                 min_following_to_follow=10,
                 max_followers_to_following_ratio=10,
                 max_following_to_followers_ratio=2,
                 min_media_count_to_follow=3,
                 max_following_to_block=2000,
                 like_delay=10,
                 unlike_delay=10,
                 follow_delay=30,
                 unfollow_delay=30,
                 comment_delay=60,
                 block_delay=30,
                 unblock_delay=30,
                 message_delay=60,
                 stop_words=('shop', 'store', 'free'),
                 verbosity=True,
                 ):
        self.api = API()

        self.total_liked = 0
        self.total_unliked = 0
        self.total_followed = 0
        self.total_unfollowed = 0
        self.total_commented = 0
        self.total_blocked = 0
        self.total_unblocked = 0
        self.total_archived = 0
        self.total_unarchived = 0
        self.total_sent_messages = 0
        self.start_time = datetime.datetime.now()

        # the time.time() of the last action
        self.last_like = 0
        self.last_unlike = 0
        self.last_follow = 0
        self.last_unfollow = 0
        self.last_comment = 0
        self.last_block = 0
        self.last_unblock = 0
        self.last_message = 0

        # limits - follow
        self.filter_users = filter_users
        self.filter_business_accounts = filter_business_accounts
        self.filter_verified_accounts = filter_verified_accounts
        self.max_likes_per_day = max_likes_per_day
        self.max_unlikes_per_day = max_unlikes_per_day
        self.max_follows_per_day = max_follows_per_day
        self.max_unfollows_per_day = max_unfollows_per_day
        self.max_comments_per_day = max_comments_per_day
        self.max_blocks_per_day = max_blocks_per_day
        self.max_unblocks_per_day = max_unblocks_per_day
        self.max_messages_per_day = max_messages_per_day
        self.max_likes_to_like = max_likes_to_like
        self.max_followers_to_follow = max_followers_to_follow
        self.min_followers_to_follow = min_followers_to_follow
        self.max_following_to_follow = max_following_to_follow
        self.min_following_to_follow = min_following_to_follow
        self.max_followers_to_following_ratio = max_followers_to_following_ratio
        self.max_following_to_followers_ratio = max_following_to_followers_ratio
        self.min_media_count_to_follow = min_media_count_to_follow
        self.stop_words = stop_words

        # limits - block
        self.max_following_to_block = max_following_to_block

        # delays
        self.like_delay = like_delay
        self.unlike_delay = unlike_delay
        self.follow_delay = follow_delay
        self.unfollow_delay = unfollow_delay
        self.comment_delay = comment_delay
        self.block_delay = block_delay
        self.unblock_delay = unblock_delay
        self.message_delay = message_delay

        # current following
        self.following = []

        # proxy
        self.proxy = proxy

        # white and blacklists
        self.whitelist = []
        if whitelist:
            self.whitelist = read_list_from_file(whitelist)
        self.blacklist = []
        if blacklist:
            self.blacklist = read_list_from_file(blacklist)

        self.verbosity = verbosity

        # comment file
        self.comments = []
        if comments_file:
            self.comments = read_list_from_file(comments_file)

        self.logger = self.api.logger
        self.logger.info('Instabot Started')

    @property
    def user_id(self):
        # For compatibility
        return self.api.user_id

    @property
    def username(self):
        # For compatibility
        return self.api.username

    @property
    def password(self):
        # For compatibility
        return self.api.password

    @property
    def last_json(self):
        # For compatibility
        return self.api.last_json

    def version(self):
        try:
            from pip._vendor import pkg_resources
        except ImportError:
            import pkg_resources
        return next((p.version for p in pkg_resources.working_set if p.project_name.lower() == 'instabot'), "No match")

    def logout(self):
        save_checkpoint(self)
        self.api.logout()
        self.logger.info("Bot stopped. "
                         "Worked: %s", datetime.datetime.now() - self.start_time)
        self.print_counters()

    def login(self, **args):
        if self.proxy:
            args['proxy'] = self.proxy
        if self.api.login(**args) is False:
            return False
        self.prepare()
        signal.signal(signal.SIGTERM, self.logout)
        atexit.register(self.logout)
        return True

    def prepare(self):
        storage = load_checkpoint(self)
        if storage is not None:
            self.total_liked, self.total_unliked, self.total_followed, self.total_unfollowed, self.total_commented, self.total_blocked, self.total_unblocked, self.api.total_requests, self.start_time, self.total_archived, self.total_unarchived, self.total_sent_messages = storage
        if not self.whitelist:
            self.whitelist = check_whitelists(self)
        self.whitelist = self.convert_whitelist(self.whitelist)
        self.blacklist = [self.convert_to_user_id(u) for u in self.blacklist
                          if u is not None]

    def convert_whitelist(self, usernames):
        """
        Will convert every username in the whitelist to the user id.
        """
        ret = []
        for u in usernames:
            uid = self.convert_to_user_id(u)
            if uid and uid not in ret:
                ret.append(uid)
            else:
                print("WARNING: Whitelisted user '%s' not found" % u)
        return ret

    def print_counters(self):
        if self.total_liked:
            self.logger.info("Total liked: %d", self.total_liked)
        if self.total_unliked:
            self.logger.info("Total unliked: %d", self.total_unliked)
        if self.total_followed:
            self.logger.info("Total followed: %d", self.total_followed)
        if self.total_unfollowed:
            self.logger.info("Total unfollowed: %d", self.total_unfollowed)
        if self.total_commented:
            self.logger.info("Total commented: %d", self.total_commented)
        if self.total_blocked:
            self.logger.info("Total blocked: %d", self.total_blocked)
        if self.total_unblocked:
            self.logger.info("Total unblocked: %d", self.total_unblocked)
        if self.total_archived:
            self.logger.info("Total archived: %d", self.total_archived)
        if self.total_unarchived:
            self.logger.info("Total unarchived: %d", self.total_unarchived)
        if self.total_sent_messages:
            self.logger.info("Total sent messages: %d", self.total_sent_messages)
        self.logger.info("Total requests: %d", self.api.total_requests)

    # getters

    def get_your_medias(self, as_dict=False):
        """
        Returns your media ids. With parameter as_dict=True returns media as dict.
        :type as_dict: bool
        """
        return get_your_medias(self, as_dict)

    def get_archived_medias(self, as_dict=False):
        """
        Returns your archived media ids. With parameter as_dict=True returns media as dict.
        :type as_dict: bool
        """
        return get_archived_medias(self, as_dict)

    def get_timeline_medias(self):
        return get_timeline_medias(self)

    def get_popular_medias(self):
        return get_popular_medias(self)

    def get_user_medias(self, user_id, filtration=True, is_comment=False):
        return get_user_medias(self, user_id, filtration, is_comment)

    def get_total_user_medias(self, user_id):
        return get_total_user_medias(self, user_id)

    def get_hashtag_medias(self, hashtag, filtration=True):
        return get_hashtag_medias(self, hashtag, filtration)

    def get_total_hashtag_medias(self, hashtag, amount=100, filtration=False):
        return get_total_hashtag_medias(self, hashtag, amount, filtration)

    def get_geotag_medias(self, geotag, filtration=True):
        return get_geotag_medias(self, geotag, filtration)

    def get_locations_from_coordinates(self, latitude, longitude):
        return get_locations_from_coordinates(self, latitude, longitude)

    def get_media_info(self, media_id):
        return get_media_info(self, media_id)

    def get_timeline_users(self):
        return get_timeline_users(self)

    def get_hashtag_users(self, hashtag):
        return get_hashtag_users(self, hashtag)

    def get_geotag_users(self, geotag):
        return get_geotag_users(self, geotag)

    def get_user_id_from_username(self, username):
        return get_user_id_from_username(self, username)

    def get_username_from_user_id(self, user_id):
        return get_username_from_user_id(self, user_id)

    def get_user_info(self, user_id):
        return get_user_info(self, user_id)

    def get_user_followers(self, user_id, nfollows=None):
        return get_user_followers(self, user_id, nfollows)

    def get_user_following(self, user_id, nfollows=None):
        return get_user_following(self, user_id, nfollows)

    def get_media_likers(self, media_id):
        return get_media_likers(self, media_id)

    def get_media_comments(self, media_id, only_text=False):
        return get_media_comments(self, media_id, only_text)

    def get_comment(self):
        return get_comment(self)

    def get_media_commenters(self, media_id):
        return get_media_commenters(self, media_id)

    def get_media_owner(self, media):
        return get_media_owner(self, media)

    def get_user_likers(self, user_id, media_count=10):
        return get_user_likers(self, user_id, media_count)

    def get_media_id_from_link(self, link):
        return get_media_id_from_link(self, link)

    def search_users(self, query):
        return search_users(self, query)

    def convert_to_user_id(self, usernames):
        return convert_to_user_id(self, usernames)

    # like

    def like(self, media_id):
        return like(self, media_id)

    def like_medias(self, media_ids):
        return like_medias(self, media_ids)

    def like_timeline(self, amount=None):
        return like_timeline(self, amount)

    def like_user(self, user_id, amount=None, filtration=True):
        return like_user(self, user_id, amount, filtration)

    def like_hashtag(self, hashtag, amount=None):
        return like_hashtag(self, hashtag, amount)

    def like_geotag(self, geotag, amount=None):
        return like_geotag(self, geotag, amount)

    def like_users(self, user_ids, nlikes=None, filtration=True):
        return like_users(self, user_ids, nlikes, filtration)

    def like_followers(self, user_id, nlikes=None, nfollows=None):
        return like_followers(self, user_id, nlikes, nfollows)

    def like_following(self, user_id, nlikes=None):
        return like_following(self, user_id, nlikes)

    # unlike

    def unlike(self, media_id):
        return unlike(self, media_id)

    def unlike_medias(self, media_ids):
        return unlike_medias(self, media_ids)

    def unlike_user(self, user):
        return unlike_user(self, user)

    # photo

    def download_photo(self, media_id, path='photos/', filename=None, description=False):
        return download_photo(self, media_id, path, filename, description)

    def download_photos(self, medias, path='photos/', description=False):
        return download_photos(self, medias, path, description)

    def upload_photo(self, photo, caption=None, upload_id=None):
        return upload_photo(self, photo, caption, upload_id)

    # video

    def upload_video(self, video, thumbnail, caption=''):
        return upload_video(self, video, thumbnail, caption)

    # follow

    def follow(self, user_id):
        return follow(self, user_id)

    def follow_users(self, user_ids):
        return follow_users(self, user_ids)

    def follow_followers(self, user_id, nfollows=None):
        return follow_followers(self, user_id, nfollows)

    def follow_following(self, user_id):
        return follow_following(self, user_id)

    # unfollow

    def unfollow(self, user_id):
        return unfollow(self, user_id)

    def unfollow_users(self, user_ids):
        return unfollow_users(self, user_ids)

    def unfollow_non_followers(self, n_to_unfollows=None):
        return unfollow_non_followers(self, n_to_unfollows)

    def unfollow_everyone(self):
        return unfollow_everyone(self)

    def update_unfollow_file(self):
        return update_unfollow_file(self)

    # direct

    def send_message(self, text, user_ids, thread_id=None):
        return send_message(self, text, user_ids, thread_id)

    def send_messages(self, text, user_ids):
        return send_messages(self, text, user_ids)

    def send_media(self, media_id, user_ids, text=None, thread_id=None):
        return send_media(self, media_id, user_ids, text, thread_id)

    def send_medias(self, media_id, user_ids, text=None):
        return send_medias(self, media_id, user_ids, text)

    def send_hashtag(self, hashtag, user_ids, text='', thread_id=None):
        return send_hashtag(self, hashtag, user_ids, text, thread_id)

    def send_profile(self, profile_user_id, user_ids, text='', thread_id=None):
        return send_profile(self, profile_user_id, user_ids, text, thread_id)

    def send_like(self, user_ids, thread_id=None):
        send_like(self, user_ids, thread_id)

    # delete

    def delete_media(self, media_id):
        return delete_media(self, media_id)

    def delete_medias(self, medias):
        return delete_medias(self, medias)

    def delete_comment(self, media_id, comment_id):
        return delete_comment(self, media_id, comment_id)

    # archive

    def archive(self, media_id, undo=False):
        return archive(self, media_id, undo)

    def unarchive(self, media_id):
        return archive(self, media_id, True)

    def archive_medias(self, medias):
        return archive_medias(self, medias)

    def unarchive_medias(self, medias):
        return unarchive_medias(self, medias)

    # comment

    def comment(self, media_id, comment_text):
        return comment(self, media_id, comment_text)

    def comment_hashtag(self, hashtag, amount=None):
        return comment_hashtag(self, hashtag, amount)

    def comment_medias(self, medias):
        return comment_medias(self, medias)

    def comment_user(self, user_id, amount=None):
        return comment_user(self, user_id, amount)

    def comment_users(self, user_ids, ncomments=None):
        return comment_users(self, user_ids, ncomments)

    def comment_geotag(self, geotag):
        return comment_geotag(self, geotag)

    def is_commented(self, media_id):
        return is_commented(self, media_id)

    # block

    def block(self, user_id):
        return block(self, user_id)

    def unblock(self, user_id):
        return unblock(self, user_id)

    def block_users(self, user_ids):
        return block_users(self, user_ids)

    def unblock_users(self, user_ids):
        return unblock_users(self, user_ids)

    def block_bots(self):
        return block_bots(self)

    # filter

    def filter_medias(self, media_items, filtration=True, quiet=False, is_comment=False):
        return filter_medias(self, media_items, filtration, quiet, is_comment)

    def check_media(self, media):
        return check_media(self, media)

    def check_user(self, user, filter_closed_acc=False, unfollowing=False):
        return check_user(self, user, filter_closed_acc, unfollowing)

    def check_not_bot(self, user):
        return check_not_bot(self, user)

    def filter_users(self, user_id_list):
        return filter_users(self, user_id_list)

    # support

    def check_if_file_exists(self, file_path, quiet=False):
        return check_if_file_exists(file_path, quiet)

    def extract_urls(self, text):
        return extract_urls(text)

    def read_list_from_file(self, file_path):
        return read_list_from_file(file_path)

    def add_whitelist(self, file_path):
        return add_whitelist(self, file_path)

    def add_blacklist(self, file_path):
        return add_blacklist(self, file_path)

    def console_print(self, text, color=None):
        return console_print(self, text, color)

    # stats

    def save_user_stats(self, username, path=""):
        return save_user_stats(self, username, path=path)
