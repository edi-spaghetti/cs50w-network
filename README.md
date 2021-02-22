# Network

Social Network style website built with React frontend and python backend.

Demo db can be set up by running the demo setup script
```bash
python demo/demo_setup.py
```

Demo video is uploaded to youtube with timestamps for the all the project 
requirements.

<iframe width="560" height="315" src="https://www.youtube.com/embed/pZmuzNnNsTM" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Below is a summary of all the main features

## Landing Page

Tried to make an interesting landing page experience with some animation. 
Originally planned to do some vector animation, but ran out of time.
After the animation finishes playing the user is automatically redirected to 
the 'All Posts' page.

## Posts

Posts are visible here for any user to see (signed in or not). Posts 
are displayed in reverse chronological order by using the `order` argument 
of the api search api method.

Posts display the username, text content, like button, edit button (if the 
post is created by the currently logged in user) and timestamp.

> Clicking on the username will redirect the user to that user's profile page

#### New Posts

New Posts can be created from the 'All Posts' page. New Posts are submitted to 
the server via api request, and on confirmation of post creation, the new post 
is add to the list of posts without needing to refresh the page.

 - Users who aren't get logged in will get redirected to the login screen.
 - Post creation is also protected server-side by an authentication check.

#### Editing / Saving

Users are able to edit their own posts by clicking the pencil icon on any post 
that was created by themselves (it doesn't appear on others' posts). This 
converts the post text to an interface where they can modify the text content 
of their post. While editing the pencil icon will be replaced with a floppy 
disk icon for saving their changes.

When the user is done making changes, they can click the save icon and an 
`update` request will be sent to the server to save the changes. Security 
measures are in place to check any update request to posts is requested by the
owner of the post - any other request will raise a permissions error. If the 
request comes back successfully the post will be converted back to it's 
original state with the new text without having to reload the page.

#### Like / Unlike

The heart icon acts as a like/unlike button. It is animated while the mouse is 
hovering over it with a subtle heartbeat motion. It also displays a counter of 
the current number of likes the post has received.

Clicking the button will submit the appropriate `update` request to add or 
remove the current user as a 'liker' of the selected post. Requests to posts 
have authentication checks, as well as permission checks to make sure the 
added/removed user matches the currently authenticated user.

## Profile

Profile page displays the number of followers the user has, as well as the
number of people that the user follows. It also displays all of the posts for 
that user, in reverse chronological order.

Profile also features a button with a different function depending on login
 - Anonymous: redirects to login page
 - Self: displays a fun(!) alert
 - Other: Toggled between Follow and Unfollow button
 
#### Follow/Unfollow Button

Clicking the button will submit an `update` request to the server via the api, 
adding or removing the current user as a follower of the profile user. Security
checks are in place with the following features

- User making the api request must be logged in
- User can only add/remove themselves from another user's followers
- User cannot add/remove themselves from their own followers


## My Feed / Following

This is a subset of posts, limited to those created by users the current user 
is following by using the `filters` parameter of the search api. It is not 
available to users who are not logged in.

## Pagination

Pagination is provided on every page that uses data from the `search` api 
request. If Previous/Next pages are available, buttons will be shown on the 
bottom of the screen which will submit a request for the next page's data.
