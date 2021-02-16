// TODO: setup bundler
//import cookie from "react-cookies"

class NewPost extends React.Component {

	render() {
		return (
			<div id="new-post-form" className="d-flex flex-column">
				<div id="new-post-title" className="p-2">
					<h4>New Post</h4>
				</div>
				<div id="new-post-content" className="p-2">
				    <textarea placeholder="Your post here" onChange={this.props.updateContent}></textarea>
				</div>
				<div id="new-post-button" className="p-2 ml-auto">
				    <button className="btn btn-primary" onClick={this.props.create}>Post</button>
				</div>
			</div>
		)
	}
}

class Post extends React.Component {

    render() {
        return (
	        <div className="row">
				<div className="col-2">
					<span className="post-item-username" onClick={(event) => this.props.viewProfile(event, this.props.username)}>{this.props.username}</span>
				</div>
				<div className="col-6">
					<span>{this.props.content}</span>
				</div>
				<div className="col-2">
					<span className="icon_heart like-post-button">
						<div className="post-like-count">
							{this.props.like_count}
						</div>
					</span>
				</div>
				<div className="col-2">
					<span>{this.props.timestamp}</span>
				</div>
			</div>
        )
    }
}

class Profile extends React.Component {

	render() {
		// TODO: redesign this widget

		var follow_btn
		if (this.props.data.can_follow) {
			if (this.props.data.is_following) {
				follow_btn = React.createElement(
					'button', {
						onClick: this.props.clickedFollowButton,
						className: 'btn btn-primary'
					}, 'Unfollow'
				)
			}
			else {
				follow_btn = React.createElement(
					'button', {
						onClick: this.props.clickedFollowButton,
						className: 'btn btn-outline-primary'
					}, 'Follow'
				)
			}
		}
		else if (this.props.data.is_self) {
			follow_btn = React.createElement(
					'button', {
						onClick: (event) => {alert('Mmm. Oh Yeah!')},
						className: 'btn btn-outline-danger'
					}, 'This Button Does Nothing... But it feels good!'
				)
		}
		else {
			// if we can't follow and the profile is not the user's own
			// profile we can assume this is an anonymous user
			follow_btn = React.createElement(
				'button', {
					onClick: (event) => {window.location.href = '/login'},
					className: 'btn btn-outline-info'
				}, 'Log in to access more features...'
			)
		}

		return (
	        <div className="d-flex flex-column user-profile">
				<h4>Profile: {this.props.data.username}</h4>
				<h4>Followers: {this.props.data.follower_count}</h4>
				<h4>Following: {this.props.data.leader_count}</h4>
				{follow_btn}
	        </div>
		)
	}
}

class App extends React.Component {

	constructor(props) {
		super(props)

		this.state = {
			page: 'home',
			pageParams: {
				data: null
			},
			csrfToken: document.querySelector(
				'input[name = "csrfmiddlewaretoken"]').value
		}

		// set navigation bar callbacks
		var mapping = {
			'network-home': this.viewHomePage,
			'my-profile': this.viewMyProfile,
			'all-posts': this.viewAllPosts,
			'my-feed': this.viewFeed
		}
		for (const [key, value] of Object.entries(mapping)) {
			var element = document.querySelector(`#${key}`)
			if (element !== null) {
				element.onclick = value
			}
		}
	}

	viewHomePage = (event) => {
		// TODO: magical landing page experience
		console.log('clicked home')
		this.setState((state) => {
			state.page = 'home'
			return state
		})
	}

	viewMyProfile = (event) => {
		this.viewProfile(
			event, document.querySelector('#my-profile').dataset.username
		)
	}

	search = (model, fields, filters, order, limit, newState) => {
		const self = this
		var returnValue

		// sanitize params
		if (!model || typeof model != 'string') {
			throw 'Model must be defined'
		}
		fields = fields || null
		filters = filters || null
		order = order || null
		limit = limit || null
		newState = newState || {}

		fetch('/api/v1/search', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			},
			body: JSON.stringify({
				model: model,
				order: order,
				fields: fields,
				filters: filters,
				limit: limit
			})
		})
		// TODO: error handling on response
		// TODO: caching (and maybe e-tags?) to avoid re-downloading data
		.then(response => response.json())
		.then(data => this.setState((state) => {
			returnValue = data
			if (newState.page !== undefined) {
				state.page = newState.page
			}
			if (newState.setData) {
				state.pageParams.data = data
			}
			return state
		}))

		return returnValue
	}

	viewAllPosts = (event) => {
		this.search(
			'post', true, null, '-timestamp', null,
			{page: 'posts', setData: true}
		)
	}

	viewFeed = (event) => {

		var username = document.querySelector('#my-profile').dataset.username
		var filters = [`username == ${username}`]
		this.search(
			'user', [{leaders: [{posts: true}]}], filters, null, 1,
			{page: 'feed', setData: true}
		)
	}

	create = (event) => {

		// create handle to this for use inside fetch
		const self = this

		fetch('/api/v1/create', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			},
			body: JSON.stringify({
				content: self.state.pageParams.content,
				model: 'post'
			})
		})
		.then(response => response.json())
		.then(data => this.insertNewPost(data))

		event.preventDefault()
	}

	insertNewPost = (new_post) => {

		// clear the new post form
		document.querySelector('#new-post-content > textarea').value = ''

		this.setState((state) => {
			// add post to state list
			// TODO: insert by sorted index
			//       currently sorting is hard coded to descending timestamp,
			//       but if I add filters and sorting this will break.
			state.pageParams.data = [new_post, ...this.state.pageParams.data]
			// clear cached state value
			state.pageParams.content = ''
		})
	}

	updateContent = (event) => {
		this.setState((state) => {
			state.pageParams.content = event.target.value
			return state
		})
	}

	viewProfile = (event, username) => {

		var fields = [
			'username', 'follower_count', 'leader_count', 'can_follow',
			'is_following', 'is_self',
			{ posts: {
				fields: ['id', 'username', 'content',
				'timestamp', 'like_count'],
				order: '-timestamp'
			}}
		]
		var filters = [`username == ${username}`]

		this.search(
			'user', fields, filters, null, 1,
			{page: 'posts', setData: true}
		)
	}

	clickedFollowButton = (event) => {
		// TODO: update api method
		console.log(event)
	}

    render() {

		var pageComponent;
		var data = [];  // init as empty array so concat below doesn't fail
		if (this.state.page === 'home') {
			// TODO: pageComponent = <Home />
		}
		else {

			if (this.state.page === 'posts') {
				pageComponent = <NewPost key={0} updateContent={this.updateContent} create={this.create}/>
				data = this.state.pageParams.data
			}
			else if (this.state.page === 'profile') {
				pageComponent = <Profile key={0} data={this.state.pageParams.data} clickedFollowButton={this.clickedFollowButton}/>
				data = this.state.pageParams.data.posts
			}
			else if (this.state.page === 'feed') {
				// TODO: pageComponent = <MyFeed />
				{leaders: [{posts: true}]}
				this.state.pageParams.data.leaders.forEach((leader) => {
					leader.posts.forEach((post) => {
						data.push(post)
					})
				})

				// TODO: sort into reverse chronological order
			}

			// map data to Post components
			data = data.map(
				post => <Post
					key={post.id}
					username={post.username}
					timestamp={post.timestamp}
					content={post.content}
					like_count={post.like_count}
					viewProfile={this.viewProfile}
				/>
			)
		}

		// add list of posts to special component
		return [pageComponent].concat(data)

    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
