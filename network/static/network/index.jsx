class Post extends React.Component {

	constructor(props) {
		super(props)
	}

    render() {
        return (
	        <div class="row">
				<div class="col-2">
					<span>{this.props.user}</span>
				</div>
				<div class="col-8">
					<span>{this.props.content}</span>
				</div>
				<div class="col-2">
					<span>{this.props.timestamp}</span>
				</div>
			</div>
        )
    }
}

class App extends React.Component {

	constructor(props) {
		super(props)

		this.state = {
			posts: []
		}
	}

	componentDidMount() {
		fetch('/api/v1/search?model=post')
		.then(response => response.json())
		.then(posts => this.setState({ posts: posts }))
	}

    render(posts) {
        return (
			this.state.posts.map(post => <Post
				user={post.user}
				timestamp={post.timestamp}
				content={post.content}
			/>)
        )
    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
