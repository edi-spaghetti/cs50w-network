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
		// TODO: login redirect for anon
		// TODO: something else for logged in user (i.e. self)

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
			page: 'posts',
			pageParams: {
				content: '',
				posts: []
			},
			csrfToken: document.querySelector(
				'input[name = "csrfmiddlewaretoken"]').value
		}
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
			state.pageParams.posts = [new_post, ...this.state.posts]
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

		const self = this

		fetch('/api/v1/search', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			},
			body: JSON.stringify({
				model: 'user',
				fields: [
					'username',
					'follower_count',
					'leader_count',
					'can_follow',
					'is_following',
					{ posts: {
						fields: ['id', 'username', 'content',
						'timestamp', 'like_count'],
						order: '-timestamp'
					}}
				],
				filters: [`username == ${username}`]
				// TODO: add limit syntax
			})
		})
		.then(response => response.json())
		// set page state to profile
		.then(data => this.setState((state) => {
			// TODO: on limit == 1, return object instead of array
			state.page = 'profile'
			state.pageParams = data[0]
			return state
		}))

	}

	clickedFollowButton = (event) => {
		// TODO: update api method
		console.log(event)
	}

	componentDidMount() {

		const self = this

		fetch('/api/v1/search', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			},
			body: JSON.stringify({
				model: 'post',
				order: '-timestamp',
				fields: true
			})
		})
		// TODO: error handling on response
		.then(response => response.json())
		.then(posts => this.setState((state) => {
			state.pageParams.posts = posts
			return state
		}))

	}

    render() {
		let data = this.state.pageParams.posts.map(
			post => <Post
				key={post.id}
				username={post.username}
				timestamp={post.timestamp}
				content={post.content}
				like_count={post.like_count}
				viewProfile={this.viewProfile}
			/>
		)

		// create the specific page's special component
		var pageComponent;
		if (this.state.page === 'posts') {
			pageComponent = <NewPost key={0} updateContent={this.updateContent} create={this.create}/>
		}
		else if (this.state.page === 'profile') {
			pageComponent = <Profile key={0} data={this.state.pageParams} clickedFollowButton={this.clickedFollowButton}/>
		}

		// add list of posts to special component
		return [pageComponent].concat(data)

    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
