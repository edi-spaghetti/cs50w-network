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

	constructor(props) {
		super(props)
	}

    render() {
        return (
	        <div className="row">
				<div className="col-2">
					<span className="post-item-username" onClick={(event) => this.props.viewProfile(event, this.props.user)}>{this.props.user}</span>
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

	constructor(props) {
		super(props)
		this.state = {
			username: props.data.username
		}
	}

	render() {
		// TODO: add followers features (buttons and summary)
		return (
	        <div className="d-flex flex-column user-profile">
				<h4>Profile: {this.state.username}</h4>
	        </div>
		)
	}
}

class App extends React.Component {

	constructor(props) {
		super(props)

		this.state = {
			page: 'posts',
			pageParams: {},
			posts: [],
			content: '',
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
				// TODO: refactor new post state data
				//       this variable is only useful for this one specific
				//       model, and would be better generalised (maybe
				//       something like incoming / outgoing data)
				content: self.state.content,
				model: 'post'
			})
		})
		.then(response => response.json())
		.then(data => this.insertNewPost(data))

		event.preventDefault()
	}

	insertNewPost = (new_post) => {

		// add post to state list
		// TODO: insert by sorted index
		//       currently sorting is harded coded to descending timestamp,
		//       but if I add filters and sorting this will break.
		this.setState({
			posts: [new_post, ...this.state.posts]
		})

		// clear the new post form
		document.querySelector('#new-post-content > textarea').value = ''
		// clear cached state value
		this.setState({
			content: ''
		})
	}

	updateContent = (event) => {
		this.setState({
			content: event.target.value
		})
	}

	viewProfile = (event, username) => {

		// TODO: fetch user's posts

		// TODO: fetch user info

		// set page state to profile
		this.setState({
			page: 'profile',
			pageParams: {
				username: username,
				posts: [],  // TODO
			}
		})
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
				fields: '*'
			})
		})
		.then(response => response.json())
		.then(posts => this.setState({ posts: posts }))
	}

    render() {
		let data = this.state.posts.map(
			post => <Post
				key={post.id}
				user={post.user}
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
			pageComponent = <Profile key={0} data={this.state.pageParams}/>
		}

		// add list of posts to special component
		return [pageComponent].concat(data)

    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
