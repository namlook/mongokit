#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009, Nicolas Clairon
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the University of California, Berkeley nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from mongokit import *

class RelatedTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.col = self.connection['test']['mongokit'] 
        
    def tearDown(self):
        self.connection()['test'].drop_collection('mongokit')
        self.connection()['test'].drop_collection('_mongometa')

    def test_simple_related(self):
        
        class Blog(Document):
            structure = {
                "blog":{"title":unicode}
            }
            
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "blog_id":unicode,
                    "content":unicode,
                },
            }

        # BlogPost is declared after Blog so we have to fill related_to after
        # BlogPost declaration
        Blog.related_to = {
          'blog_posts':{'class':self.col.BlogPost, 'target':'blog_post.blog_id'},
        }

        self.connection.register([Blog, BlogPost])
 
        blog = self.col.Blog()
        blog['_id'] = u'my blog'
        blog['title'] = u'My Blog'
        blog.save()
        
        blog_post1 = self.col.BlogPost()
        blog_post1['_id'] = 1
        blog_post1['blog_post']['blog_id'] = blog['_id']
        blog_post1['blog_post']['content'] = u'a great blog post'
        blog_post1.save()

        blog_post2 = self.col.BlogPost()
        blog_post2['_id'] = 2
        blog_post2['blog_post']['blog_id'] = blog['_id']
        blog_post2['blog_post']['content'] = u'another great blog post'
        blog_post2.save()

        blog_posts = list(blog.related.blog_posts())
        assert blog_posts == [blog_post1, blog_post2], blog_posts

    def test_multiple_related(self):
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "blog_id":unicode,
                    "content":unicode,
                },
            }
        class Author(Document):
            structure = {
                'author':{
                    'name':unicode,
                    'blog_id':unicode,
                },
            }
 
        class Blog(Document):
            structure = {
                "blog":{"title":unicode}
            }
            related_to = {
              'authors':{'class':Author, 'target':'author.blog_id'},
              'blog_posts':{'class':BlogPost, 'target':'blog_post.blog_id'},
            }
        self.connection.register([BlogPost, Author, Blog])
 
        blog = self.col.Blog()
        blog['_id'] = u'my blog'
        blog['title'] = u'My Blog'
        blog.save()
        
        blog_post1 = self.col.BlogPost()
        blog_post1['_id'] = 1
        blog_post1['blog_post']['blog_id'] = blog['_id']
        blog_post1['blog_post']['content'] = u'a great blog post'
        blog_post1.save()

        blog_post2 = self.col.BlogPost()
        blog_post2['_id'] = 2
        blog_post2['blog_post']['blog_id'] = blog['_id']
        blog_post2['blog_post']['content'] = u'another great blog post'
        blog_post2.save()

        author1 = self.col.Author()
        author1['_id'] = u'me'
        author1['author']['name'] = u'Me'
        author1['author']['blog_id'] = blog['_id']
        author1.save()

        author2 = self.col.Author()
        author2['_id'] = u'you'
        author2['author']['name'] = u'You'
        author2['author']['blog_id'] = blog['_id']
        author2.save()

        authors = list(blog.related.authors())
        assert authors == [author1, author2], authors
        blog_posts = list(blog.related.blog_posts())
        assert blog_posts == [blog_post1, blog_post2], blog_posts

    def test_multiple_related2(self):
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "blog_id":unicode,
                    "content":unicode,
                },
            }
        class Blog(Document):
            structure = {
                "blog":{"title":unicode}
            }
            related_to = {
              'blog_posts':{'class':BlogPost, 'target':'blog_post.blog_id'},
            }
        self.connection.register([BlogPost, Blog])

        blog = self.col.Blog()
        blog['_id'] = u'my blog'
        blog['title'] = u'My Blog'
        blog.save()
        
        blog_post1 = self.col.BlogPost()
        blog_post1['blog_post']['blog_id'] = blog['_id']
        blog_post1['blog_post']['content'] = u'a great blog post'
        blog_post1.save()

        blog_post2 = self.col.BlogPost()
        blog_post2['blog_post']['blog_id'] = blog['_id']
        blog_post2['blog_post']['content'] = u'another great blog post'
        blog_post2.save()


        class Author(Document):
            db_name = 'test'
            collection_name = 'mongokit'
            structure = {
                'author':{
                    'name':unicode,
                    'blog_id':unicode,
                },
            }
        self.connection.register([Author])
 
        author1 = self.col.Author()
        author1['author']['name'] = u'me'
        author1['author']['blog_id'] = blog['_id']
        author1.save()

        author2 = self.col.Author()
        author2['author']['name'] = u'you'
        author2['author']['blog_id'] = blog['_id']
        author2.save()

        Blog.related_to.update({'authors':{'class':Author, 'target':'author.blog_id'}})

        blog = self.col.Blog.get_from_id('my blog')

        authors = list(blog.related.authors())
        assert authors == [author1, author2], authors
        blog_posts = list(blog.related.blog_posts())
        assert blog_posts == [blog_post1, blog_post2], blog_posts


    def test_simple_related_with_autorefs(self):

        class Blog(Document):
            structure = {
                "blog":{"title":unicode}
            }
 
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "blog":Blog,
                    "content":unicode,
                },
            }
            use_autorefs = True

        # BlogPost is declared after Blog so we have to fill related_to after
        # BlogPost declaration
        Blog.related_to = {
          'blog_posts':{'class':BlogPost, 'target':'blog_post.blog', 'autoref':True}
        }
        self.connection.register([Blog, BlogPost])
 
        blog = self.col.Blog()
        blog['_id'] = u'my blog'
        blog['title'] = u'My Blog'
        blog.save()
        blog.related
        
        blog_post1 = self.col.BlogPost()
        blog_post1['_id'] = 1
        blog_post1['blog_post']['blog'] = blog
        blog_post1['blog_post']['content'] = u'a great blog post'
        blog_post1.save()

        blog_post2 = self.col.BlogPost()
        blog_post2['_id'] = 2
        blog_post2['blog_post']['blog'] = blog
        blog_post2['blog_post']['content'] = u'another great blog post'
        blog_post2.save()

        blog_posts = list(blog.related.blog_posts())
        assert blog_posts == [blog_post1, blog_post2], blog_posts

    def test_simple_related_with_autorefs_extra_query(self):
        class Blog(Document):
            structure = {
                "blog":{"title":unicode}
            }
 
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "blog":Blog,
                    "content":unicode,
                },
            }
            use_autorefs = True

        # BlogPost is declared after Blog so we have to fill related_to after
        # BlogPost declaration
        Blog.related_to = {
          'blog_posts':{'class':BlogPost, 'target':'blog_post.blog', 'autoref':True}
        }
        self.connection.register([Blog, BlogPost])
 
        blog = self.col.Blog()
        blog['_id'] = u'my blog'
        blog['title'] = u'My Blog'
        blog.save()
        blog.related
        
        blog_post1 = self.col.BlogPost()
        blog_post1['_id'] = 1
        blog_post1['blog_post']['blog'] = blog
        blog_post1['blog_post']['content'] = u'a great blog post'
        blog_post1.save()

        blog_post2 = self.col.BlogPost()
        blog_post2['_id'] = 2
        blog_post2['blog_post']['blog'] = blog
        blog_post2['blog_post']['content'] = u'another great blog post'
        blog_post2.save()

        blog_posts = list(blog.related.blog_posts({'blog_post.content':'a great blog post'}))
        assert blog_posts == [blog_post1], blog_posts


    def test_bad_related(self):
        
        class Blog(Document):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "blog":{"title":unicode}
            }
        class BlogPost(Document):
            db_name = "test"
            collection_name = "mongokit"
            structure = {
                "blog_post":{
                    "blog_id":unicode,
                    "content":unicode,
                },
            }

        # BlogPost is declared after Blog so we have to fill related_to after
        # BlogPost declaration
        Blog.related_to = {
          'blog_posts':{'class':BlogPost, 'target':'blog_post.blog_id'},
        }
        self.connection.register([Blog, BlogPost])
 
        blog = self.col.Blog()
        blog['_id'] = u'my blog'
        blog['title'] = u'My Blog'
        blog.save()
        blog.related
        
        blog_post1 = self.col.BlogPost()
        blog_post1['blog_post']['blog_id'] = blog['_id']
        blog_post1['blog_post']['content'] = u'a great blog post'
        blog_post1.save()

        blog_post2 = self.col.BlogPost()
        blog_post2['blog_post']['blog_id'] = blog['_id']
        blog_post2['blog_post']['content'] = u'another great blog post'
        blog_post2.save()

        try:
            blog.related.arf()
        except AttributeError:
            pass

    def test_simple_related_with_query(self):
        
        class Blog(Document):
            structure = {
                "blog":{"title":unicode}
            }
        class BlogPost(Document):
            structure = {
                "blog_post":{
                    "blog_id":unicode,
                    "content":unicode,
                },
            }

        # BlogPost is declared after Blog so we have to fill related_to after
        # BlogPost declaration
        Blog.related_to = {
          'blog_posts':{'class':BlogPost, 'target':'blog_post.blog_id'},
        }
        self.connection.register([Blog, BlogPost])
 
        blog = self.col.Blog()
        blog['_id'] = u'my blog'
        blog['title'] = u'My Blog'
        blog.save()
        
        blog_post1 = self.col.BlogPost()
        blog_post1['blog_post']['blog_id'] = blog['_id']
        blog_post1['blog_post']['content'] = u'a great blog post'
        blog_post1.save()

        blog_post2 = self.col.BlogPost()
        blog_post2['blog_post']['blog_id'] = blog['_id']
        blog_post2['blog_post']['content'] = u'another great blog post'
        blog_post2.save()

        blog_posts = list(blog.related.blog_posts({'blog_post.content':'a great blog post'}))
        assert blog_posts == [blog_post1], blog_posts

    def test_related_with_complex_target(self):
        class Article(Document):
            structure = {
                'article': {
                    'title':unicode,
                    'tags':{unicode:int},
                }
            }
        class Tag(Document):
            structure = {
                'tag':{
                    'title':unicode,
                }
            }
            related_to = {'articles':{'class':Article, 'target':lambda x:{'article.tags.%s' % x:{'$gt':1}}}}
        self.connection.register([Article, Tag])

        foo = self.col.Tag()
        foo['_id'] = u'foo'
        foo['tag']['title'] = u'Foo'
        foo.save()

        bar = self.col.Tag()
        bar['_id'] = u'bar'
        bar['tag']['title'] = u'Bar'
        bar.save()

        article1 = self.col.Article()
        article1['_id'] = u'article1'
        article1['article']['title'] = u'First article'
        article1['article']['tags'][u'foo'] = 2
        article1['article']['tags'][u'bar'] = 3
        article1.save()
        
        article2 = self.col.Article()
        article2['_id'] = u'article2'
        article2['article']['title'] = u'Second article'
        article2['article']['tags'][u'foo'] = 0
        article2['article']['tags'][u'bar'] = 2
        article2.save()
        
        articles = list(bar.related.articles())
        assert len(articles) == 2, articles
        assert articles == [article1, article2]
        articles = list(foo.related.articles())
        assert len(articles) == 1
        assert articles == [article1]

    def test_related_with_complex_target_in_list(self):
        class Article(Document):
            structure = {
                'article': {
                    'title':unicode,
                    'tags':[unicode],
                }
            }
        class Tag(Document):
            structure = {
                'tag':{
                    'title':unicode,
                }
            }
            related_to = {'articles':{'class':Article, 'target':'article.tags'}}
        self.connection.register([Article, Tag])

        foo = self.col.Tag()
        foo['_id'] = u'foo'
        foo['tag']['title'] = u'Foo'
        foo.save()

        bar = self.col.Tag()
        bar['_id'] = u'bar'
        bar['tag']['title'] = u'Bar'
        bar.save()

        spam = self.col.Tag()
        spam['_id'] = u'spam'
        spam['tag']['title'] = u'Spam'
        spam.save()


        article1 = self.col.Article()
        article1['_id'] = u'article1'
        article1['article']['title'] = u'First article'
        article1['article']['tags'] = [u'foo', u'spam']
        article1.save()
        
        article2 = self.col.Article()
        article2['_id'] = u'article2'
        article2['article']['title'] = u'Second article'
        article2['article']['tags'] = [u'foo', u'bar']
        article2.save()
        
        articles = list(bar.related.articles())
        assert len(articles) == 1, articles
        assert articles == [article2]
        articles = list(foo.related.articles())
        assert len(articles) == 2
        assert articles == [article1, article2]

    def test_related_with_complex_target_in_list_with_autorefs(self):
        class Tag(Document):
            structure = {
                'tag':{
                    'title':unicode,
                }
            }

        class Article(Document):
            use_autorefs = True
            structure = {
                'article': {
                    'title':unicode,
                    'tags':[Tag],
                }
            }

        Tag.related_to = {'articles':{'class':Article, 'target':'article.tags', 'autoref':True}}
        self.connection.register([Article, Tag])

        foo = self.col.Tag()
        foo['_id'] = u'foo'
        foo['tag']['title'] = u'Foo'
        foo.save()

        bar = self.col.Tag()
        bar['_id'] = u'bar'
        bar['tag']['title'] = u'Bar'
        bar.save()

        spam = self.col.Tag()
        spam['_id'] = u'spam'
        spam['tag']['title'] = u'Spam'
        spam.save()


        article1 = self.col.Article()
        article1['_id'] = u'article1'
        article1['article']['title'] = u'First article'
        article1['article']['tags'] = [foo, spam]
        article1.save()
        
        article2 = self.col.Article()
        article2['_id'] = u'article2'
        article2['article']['title'] = u'Second article'
        article2['article']['tags'] = [foo, bar]
        article2.save()
        
        articles = list(bar.related.articles())
        assert len(articles) == 1, articles
        assert articles == [article2]
        articles = list(foo.related.articles())
        assert len(articles) == 2
        assert articles == [article1, article2]


